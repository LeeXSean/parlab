---
title: A2 · Task system
---

# Assignment 2 · Task system

<span class="lab-meta">CS149 · Completed</span>

The implementation develops from one shared launch into a scheduler for a graph
of launches. Workers claim work under a mutex, run the callback without it, and
return to update completion state.

A task is one callback; a launch contains the tasks submitted by one `run()` or
`runAsyncWithDeps()` call. `TaskID` identifies the launch. Member names end in
`_`; calls use `()`. The overview separates the caller, shared state, and workers:

```text
 +----------------------+           +----------------------------------------+
 | Caller               |           | Shared state                           |
 | runAsyncWithDeps()   |-----+     |                                        |
 | run()                |     +---->| waiting_map_ ----> waiting_            |
 | sync()               |     |     |                        |               |
 |                      |     |     |               prev_.empty()            |
 | done_.wait(lk)       |     |     |                        v               |
 +-------------+--------+     +---->| ready_map_   ----> ready_              |
               |                    +----------------------------------------+
               |                                               |
               |                                               v
               |                                 +--------------------------+
               |                                 | worker_                  |
               |                                 | thread_fn()              |
               |                                 +--------------------------+
               |                                               | lk.unlock()
               |                                               v
               |                                 +--------------------------+
               |                                 | runnable->runTask(...)   |
               |                                 +--------------------------+
               |                                               | lk.lock()
               |                                               v
               |                      +--------------------------------------+
               |                      | num_workers_--                       |
               +----------------------| prev_.erase(...)                     |
                 done_.notify_one()   | ready_.splice(...)                   |
                                      | ready_.erase(...)                    |
                                      +--------------------------------------+
```

Submission takes the lower entry into `ready_` when no unfinished dependency
remains; otherwise it takes the upper entry into `waiting_`. A callback return
decrements `num_workers_`. The dependency updates and node removal shown below
it require `num_left_tasks_ == 0 && num_workers_ == 0`; they happen once per
completed launch. Workers notify `done_` when both lists are empty. The Part A
and Part B diagrams expand this overview; their captions identify omitted guards.

Part A keeps `runnable_`, `num_total_tasks_`, `num_left_tasks_`, and
`num_workers_` on the task-system object. Part B moves these four fields into
each `TaskNode` and adds dependency edges. The constructor starts the sleeping
workers; the caller submits nodes; workers advance the graph as launches finish.

| Part | Contents |
| --- | --- |
| [Part A · Thread pools](part-a.md) | Shared counters, three worker lifetimes, and caller/worker handoff |
| [Part B · Task graphs](part-b.md) | Node submission, worker execution, and a graph traced through the lists |

[Appendix · Measurements and checks](measurements.md) ·
[Handout](https://github.com/stanford-cs149/asst2)
