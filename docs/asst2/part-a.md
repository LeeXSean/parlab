---
title: A2 · Thread pools
---

# Part A · One shared launch

All three implementations use the same work-distribution idea: publish one
`runnable_` and let workers claim task IDs from a shared counter. Each worker can
execute several tasks; `num_threads_` bounds the workers created.

## Members

Each class derives directly from `ITaskSystem`; the additions below compare
their designs. `TaskSystemSerial` adds no data members and executes a local loop.

`TaskSystemParallelSpawn` introduces the shared launch state:

| Member | Role and changes |
| --- | --- |
| `num_threads_` | Constructor argument; fixed worker count. |
| `runnable_` | `nullptr` → caller's pointer → `nullptr` after completion. |
| `num_total_tasks_` | Initially `0`; set by `run()`, fixed during that launch. |
| `num_left_tasks_` | Initially `0`; set to the launch size, decremented on claim. |
| `num_workers_` | Initially `0`; incremented on claim, decremented after the callback. |
| `mutex_` | Shared mutex, allocated at construction and deleted at destruction. |

The pool versions retain those members and add:

| Class | Added members | Purpose |
| --- | --- | --- |
| `TaskSystemParallelThreadPoolSpinning` | `worker_`, `flag_` | Persistent worker array; atomic `flag_` stays `true` until shutdown. |
| `TaskSystemParallelThreadPoolSleeping` | `undone_`, `done_` | Workers wait on `undone_`; the caller waits on `done_`. |

Part A stores the mutex and condition variables through pointers. The caller
owns the runnable and keeps it alive until `run()` returns.

`num_left_tasks`, `num_total_tasks`, and `lk` are local variables from the source.

## 1. Claim, compute, account

```text
                         thread_fn()
                               |
                               v
          +------------------------------------------+
          | num_left_tasks = num_left_tasks_         |
     +--->| num_total_tasks = num_total_tasks_       |
     |    | num_left_tasks_--                        |
     |    | num_workers_++                           |
     |    +------------------------------------------+
     |                         | mutex_->unlock()
     |                         v
     |    +------------------------------------------+
     |    | runnable_->runTask(num_left_tasks - 1,   |
     |    |                    num_total_tasks)      |
     |    +------------------------------------------+
     |                         | mutex_->lock()
     |                         v
     |    +------------------------------------------+
     |    | num_workers_--                           |
     |    +------------------------------------------+
     |                         |
     +-------------------------+
            num_left_tasks_ > 0
```

The diagram starts with `*mutex_` held and
`runnable_ && num_left_tasks_ != 0`. Pool workers also check `!flag_` at the
start of their outer loop and exit if it is true. Idle behavior differs between
the three versions, as shown below. Exact entry and loop guards are in each
class's `thread_fn()` in `asst2/part_a/tasksys.cpp`.

`num_left_tasks_` counts unclaimed tasks. `num_workers_` counts workers executing
a claimed task. A worker saves the old task count, decrements it, and calls
`runTask(num_left_tasks - 1, num_total_tasks)`, so IDs are assigned from `N - 1`
down to `0`.

Only claiming and accounting hold the mutex. The callback runs outside it.
`run()` recognizes completion when **both counters are zero**; all IDs may have
been claimed while workers are still computing.

Spawn releases the mutex between worker-loop iterations. The spinning and
sleeping pools can keep it from accounting through the next claim.

For a three-task launch `P`, one possible two-worker execution is:

```text
 Event                         num_total_tasks_  num_left_tasks_  num_workers_
 constructed                           0                0              0
 run(P, 3): runnable_ = P               3                3              0
 claim task 2                          3                2              1
 claim task 1                          3                1              2
 finish task 2                         3                1              1
 claim task 0                          3                0              2
 finish task 1                         3                0              1
 finish task 0                         3                0              0
 run(): runnable_ = nullptr            3                0              0
```

`num_total_tasks_` retains the completed launch's size until the next `run()`.
The pointer is cleared only after both live counters reach zero. Spawn and spin
start each subsequent launch with the previous completion's zero active count;
the sleeping version also explicitly assigns `num_workers_ = 0` when publishing.

## 2. Change the worker lifetime

This timeline labels thread actions across two calls:

```text
               ctor        run #1             gap       run #2          dtor
               ----        ------             ---       ------          ----
 Always spawn  (none)      [create/work/join]  (none)    [create/work/join]  -

 Spinning      [create] --> [work] ----------> [spin] --> [work] ------> [stop/join]

 Sleeping      [create] --> [work] ----------> [wait] --> [work] ------> [wake/join]
               |                                                          |
               +---------------- same pool workers -----------------------+
```

Spawn's local `worker` array is created, joined, and deleted inside `run()`.
Both pools start `worker_` in the constructor and join it in the destructor.
`flag_` changes from `true` to `false` under the mutex at shutdown; sleep also
notifies `undone_` before joining. Shared storage is deleted after the joins.

## 3. Hand a launch to the sleeping pool

```text
   run()                                                 thread_fn()
   |                                                     |
   | runnable_ = P                                       |
   | num_total_tasks_ = N                                |
   | num_left_tasks_ = N                                 |
   | num_workers_ = 0                                    |
   | lk.unlock()                                         |
   +-------------- undone_->notify_all() ---------------->
   |                                                     | lk.lock()
   | lk.lock()                                           | num_left_tasks_--
   |                                                     | num_workers_++
   | done_->wait(lk)                                     | lk.unlock()
   |                                                     | runnable_->runTask(...)
   |                                                     | lk.lock()
   |                                                     | num_workers_--
   |                                                     |
   <-------------- done_->notify_one() ------------------+
   |                                                     |
   |                                                     |
   | num_left_tasks_ == 0 && num_workers_ == 0           |
   | runnable_ = nullptr                                 | undone_->wait(lk)
   | lk.unlock()                                         |
   |                                                     |
   v                                                     v
```

The diagram follows a call that waits for completion. `P` is the runnable
pointer and `N` the launch size. The omitted wait conditions are:

- Before claiming, a worker waits on `undone_` if
  `!runnable_ || num_left_tasks_ == 0`.
- After a callback, if `num_left_tasks_ == 0`, the worker leaves its task loop
  when `num_workers_ == 0`; otherwise it waits on `undone_`.
- The caller clears `runnable_` when both counters are zero; otherwise it waits
  on `done_`. It checks again after waking, so a call may also finish without
  taking the illustrated wait path.

These checks hold `*mutex_`; `wait(lk)` releases it while sleeping and reacquires
it before returning. Workers notify `done_` after leaving their task loop and
remain alive for later calls. The full branches are in the sleeping pool's
`thread_fn()` and `run()` in `asst2/part_a/tasksys.cpp`.

[Part B · Multiple launches and dependencies](part-b.md)
