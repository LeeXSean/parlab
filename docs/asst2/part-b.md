---
title: A2 · Task graphs
---

# Part B · A graph of launches

The single shared launch from Part A becomes a `TaskNode`. Each node stores its
`runnable_`, task counters, unfinished predecessors (`prev_`), and successors
(`next_`). The system's `taskID_` counter assigns each launch its ID.

## Members

Part A stores the launch fields on the pool; Part B moves them into each node:

```text
 runnable_          -----+       ready_ / waiting_
 num_total_tasks_   -----+              |
 num_left_tasks_    -----+-----> TaskNode
 num_workers_       -----+       |-- runnable_
                                |-- num_total_tasks_
                                |-- num_left_tasks_
                                |-- num_workers_
                                |-- taskID_
                                |-- prev_
                                +-- next_
```

Each node starts with the caller's pointer, its total task count, the same count
of unclaimed tasks, and zero active workers. The pointer and total remain fixed;
claims and callback returns change the two live counters as in Part A. The node
also adds:

| Field | Role and changes |
| --- | --- |
| `taskID_` | This launch's assigned ID; fixed until removal. |
| `prev_` | Unfinished predecessor IDs; completion removes them until empty. |
| `next_` | Initially empty; later dependent submissions append their IDs. Completion walks these edges. |

The pool's members are:

| Members | Role and changes |
| --- | --- |
| `num_threads_`, `worker_`, `flag_` | Fixed worker count and persistent array; atomic `flag_` changes from `true` to `false` at shutdown. |
| `taskID_` | Next unused launch ID, starting at `0`; each accepted launch increments it. `sync()` does not reset it. |
| `waiting_`, `waiting_map_` | Initially empty; nodes with unfinished predecessors and their `ID → iterator` index; nodes leave when unblocked. |
| `ready_`, `ready_map_` | Initially empty; dependency-ready nodes and their index; nodes stay until all their callbacks finish. |
| `mutex_` | Protects ID allocation, lists, maps, dependency edges, and counters. |
| `undone_`, `done_` | Workers wait on `undone_`; the caller waits on `done_`. |

Unlike Part A, the mutex and condition variables are value members. They are
constructed before workers start and destroyed after the destructor joins them.
The system's `taskID_` advances; each node's `taskID_` is a fixed copy.

`taskID`, `deps_fn`, `ready_node`, `next_node`, `prev_node`, and `lk` are local
variables from the source.

## 1. Submit and connect a node

```text
                        runAsyncWithDeps()
                                 |
                   +---------------------------+
                   | mutex_.lock()             |
                   | taskID = taskID_++        |
                   | deps_fn = deps            |
                   +---------------------------+
                                 |
             +---------------------------------------+
             | waiting_map_.find(deps[i])            |
             | ready_map_.find(deps[i])              |
             | deps_fn.erase(...)                    |
             +---------------------------------------+
                                 |
                         deps_fn.empty()
                     true /           \ false
                         v               v
   +-----------------------------+   +--------------------------------------+
   | ready_.push_back(...)       |   | prev_node->next_.push_back(taskID)   |
   | ready_map_[taskID] = ...    |   | waiting_.push_back(...)              |
   | prev_ = []                  |   | waiting_map_[taskID] = ...           |
   +-----------------------------+   | prev_ = deps_fn                      |
                  |                  +--------------------------------------+
                  |                                      |
                  +-------------------+------------------+
                                      v
                        +----------------------------+
                        | mutex_.unlock()            |
                        | undone_.notify_all()       |
                        | return taskID              |
                        +----------------------------+
```

The diagram starts after the input guard: a null runnable or zero tasks returns
`-1` before allocating an ID. Empty `deps` skips the lookup box and enters
`ready_` directly. Otherwise the box repeats for each dependency, and
`deps_fn.erase(...)` runs only when that valid ID is absent from both maps,
meaning its launch has completed. These checks and edge updates hold `mutex_`.
Exact branches are in `runAsyncWithDeps()` in `asst2/part_b/tasksys.cpp`.

The maps store iterators to nodes in their corresponding lists. Workers may
start execution while the caller submits later nodes.

## 2. Execute and advance the graph

```text
                            thread_fn()
                                  |
                                  v
             +----------------------------------------+<--------------------+
             | ready_                                 |                     |
             | num_left_tasks_ > 0                    |                     |
             +----------------------------------------+                     |
                                  |                                         |
                          true    |    false --> undone_.wait(lk) ----------+
                                  v                                         |
             +----------------------------------------+                     |
             | num_left_tasks_--                      |                     |
             | num_workers_++                         |                     |
             +----------------------------------------+                     |
                                  | lk.unlock()                             |
                                  v                                         |
             +----------------------------------------+                     |
             | runnable->runTask(...)                 |                     |
             +----------------------------------------+                     |
                                  | lk.lock()                               |
                                  v                                         |
             +----------------------------------------+                     |
             | num_workers_--                         |                     |
             | num_left_tasks_ == 0 &&                |                     |
             | num_workers_ == 0                      |                     |
             +----------------------------------------+                     |
                          true    |    false -------------------------------+
                                  v                                         |
             +----------------------------------------+                     |
             | next_node->prev_.erase(...)            |                     |
             | if (next_node->prev_.empty())          |                     |
             |   ready_.splice(...)                   |                     |
             |   ready_map_[taskID] = ...             |                     |
             |   waiting_map_.erase(taskID)           |                     |
             |   undone_.notify_all()                 |                     |
             | ready_map_.erase(...)                  |                     |
             | ready_.erase(...) / ready_.pop_front() |                     |
             +----------------------------------------+                     |
                                  |                                         |
               ready_.empty() && waiting_.empty() -- false -----------------+
                                  | true
                                  v
                             lk.unlock()
                           done_.notify_one()
```

The diagram shows the inner loop, entered only when `!ready_.empty()`. The
outer loop first exits on `!flag_` and waits on `undone_` when
`ready_.empty() && waiting_.empty()`. After waking, it rechecks emptiness before
entering the inner loop. Unqualified counters belong to the selected node;
`next_node` is a successor iterator. The worker copies the selected pointer and
counts into locals before unlocking for the callback. All queue, edge, and
counter updates hold `mutex_`.

Workers scan `ready_` past nodes with no unclaimed tasks. A node with
`num_left_tasks_ == 0` may still have active workers, so it remains in the list.
If no task is available, the worker waits on `undone_` and selects again after
waking.

Completion visits each successor in `next_`. The successor moves to `ready_`
only after its `prev_` becomes empty. `splice` transfers the same node and
preserves its iterator for the map update.

The diagram groups two cleanup checks. Non-front removal requires both counters
to be zero and `ready_node != ready_.begin()`. The code then independently checks
the front node's two counters before using `pop_front`. Both paths keep
`mutex_` held through dependency updates and node removal. See `thread_fn()`
in `asst2/part_b/tasksys.cpp` for the exact scan, wait, and cleanup branches.

## 3. Follow one graph through the lists

The letters A, B, C, and D below name launches with IDs `0`, `1`, `2`, and `3`.
Each listed `taskID_` is also a key in the corresponding map. The pool has two
workers, and submission advances the system's `taskID_` from `0` to `4`.

```text
                         +---- B ----+
                         |           |
                  A -----+           +---- D
                         |           |
                         +---- C ----+

 +----------------+------------------------------------+------------------------------------+
 | Event          | ready_ + ready_map_                | waiting_ + waiting_map_            |
 +----------------+------------------------------------+------------------------------------+
 | Submitted      | taskID_=0; prev_=[]                | taskID_=1; prev_=[0]               |
 |                | next_=[1,2]                        | next_=[3]                          |
 |                | num_left_tasks_=2; num_workers_=0  | num_left_tasks_=1; num_workers_=0  |
 |                |                                    | taskID_=2; prev_=[0]               |
 |                |                                    | next_=[3]                          |
 |                |                                    | num_left_tasks_=1; num_workers_=0  |
 |                |                                    | taskID_=3; prev_=[1,2]             |
 |                |                                    | next_=[]                           |
 |                |                                    | num_left_tasks_=1; num_workers_=0  |
 +----------------+------------------------------------+------------------------------------+
 | 0 finishes     | taskID_=1; prev_=[]                | taskID_=3; prev_=[1,2]             |
 |                | next_=[3]                          | next_=[]                           |
 |                | num_left_tasks_=1; num_workers_=0  | num_left_tasks_=1; num_workers_=0  |
 |                | taskID_=2; prev_=[]                |                                    |
 |                | next_=[3]                          |                                    |
 |                | num_left_tasks_=1; num_workers_=0  |                                    |
 +----------------+------------------------------------+------------------------------------+
 | 1 finishes     | taskID_=2; prev_=[]                | taskID_=3; prev_=[2]               |
 | 2 computing    | next_=[3]                          | next_=[]                           |
 |                | num_left_tasks_=0; num_workers_=1  | num_left_tasks_=1; num_workers_=0  |
 +----------------+------------------------------------+------------------------------------+
 | 2 finishes     | taskID_=3; prev_=[]                | []                                 |
 |                | next_=[]                           |                                    |
 |                | num_left_tasks_=1; num_workers_=0  |                                    |
 +----------------+------------------------------------+------------------------------------+
 | 3 finishes     | []                                 | []                                 |
 +----------------+------------------------------------+------------------------------------+
```

All four launches are submitted before a worker claims a task. A has two tasks;
B, C, and D have one each. B and C can run concurrently after A finishes. If B
finishes first, D still waits for C. C stays in `ready_` with
`num_left_tasks_ = 0` and `num_workers_ = 1`. Their completion order may reverse.

Node removal destroys that launch record and its vectors. It does not delete
the caller's runnable.
Removing the ID from its map lets later submissions recognize it as completed.

## 4. Return to the caller

The three entry points share the sleeping workers, with these distinct paths:

| Entry point | Queue operation | Return condition |
| --- | --- | --- |
| `run()` | Append a dependency-free node to `ready_` and `ready_map_`; notify `undone_` | `ready_.empty()` |
| `runAsyncWithDeps()` | Follow the submission diagram | Node published and ID returned |
| `sync()` | Add no node; wait on `done_` | `ready_.empty() && waiting_.empty()` |

The handout uses one calling thread and separates synchronous and asynchronous
launches. In synchronous mode `waiting_` stays empty, so `run()` checks only
`ready_`.

The worker notifies `done_` after it observes both lists empty. The caller
rechecks its condition under `mutex_`. Completed launches have already been
removed, so this also accounts for the end of their callbacks.

After this example's `sync()`, all four containers are empty, the system's
`taskID_` remains `4`, and `flag_` remains `true`. The workers stay alive.

Shutdown sets `flag_ = false` under the mutex, notifies `undone_`, joins every
worker, and deletes `worker_`.
