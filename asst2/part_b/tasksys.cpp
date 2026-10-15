#include "tasksys.h"


IRunnable::~IRunnable() {}

ITaskSystem::ITaskSystem(int num_threads) {}
ITaskSystem::~ITaskSystem() {}

/*
 * ================================================================
 * Serial task system implementation
 * ================================================================
 */

const char* TaskSystemSerial::name() {
    return "Serial";
}

TaskSystemSerial::TaskSystemSerial(int num_threads): ITaskSystem(num_threads) {
}

TaskSystemSerial::~TaskSystemSerial() {}

void TaskSystemSerial::run(IRunnable* runnable, int num_total_tasks) {
    for (int i = 0; i < num_total_tasks; i++) {
        runnable->runTask(i, num_total_tasks);
    }
}

TaskID TaskSystemSerial::runAsyncWithDeps(IRunnable* runnable, int num_total_tasks,
                                          const std::vector<TaskID>& deps) {
    for (int i = 0; i < num_total_tasks; i++) {
        runnable->runTask(i, num_total_tasks);
    }

    return 0;
}

void TaskSystemSerial::sync() {
    return;
}

/*
 * ================================================================
 * Parallel Task System Implementation
 * ================================================================
 */

const char* TaskSystemParallelSpawn::name() {
    return "Parallel + Always Spawn";
}

TaskSystemParallelSpawn::TaskSystemParallelSpawn(int num_threads): ITaskSystem(num_threads) {
    // NOTE: CS149 students are not expected to implement TaskSystemParallelSpawn in Part B.
}

TaskSystemParallelSpawn::~TaskSystemParallelSpawn() {}

void TaskSystemParallelSpawn::run(IRunnable* runnable, int num_total_tasks) {
    // NOTE: CS149 students are not expected to implement TaskSystemParallelSpawn in Part B.
    for (int i = 0; i < num_total_tasks; i++) {
        runnable->runTask(i, num_total_tasks);
    }
}

TaskID TaskSystemParallelSpawn::runAsyncWithDeps(IRunnable* runnable, int num_total_tasks,
                                                 const std::vector<TaskID>& deps) {
    // NOTE: CS149 students are not expected to implement TaskSystemParallelSpawn in Part B.
    for (int i = 0; i < num_total_tasks; i++) {
        runnable->runTask(i, num_total_tasks);
    }

    return 0;
}

void TaskSystemParallelSpawn::sync() {
    // NOTE: CS149 students are not expected to implement TaskSystemParallelSpawn in Part B.
    return;
}

/*
 * ================================================================
 * Parallel Thread Pool Spinning Task System Implementation
 * ================================================================
 */

const char* TaskSystemParallelThreadPoolSpinning::name() {
    return "Parallel + Thread Pool + Spin";
}

TaskSystemParallelThreadPoolSpinning::TaskSystemParallelThreadPoolSpinning(int num_threads): ITaskSystem(num_threads) {
    // NOTE: CS149 students are not expected to implement TaskSystemParallelThreadPoolSpinning in Part B.
}

TaskSystemParallelThreadPoolSpinning::~TaskSystemParallelThreadPoolSpinning() {}

void TaskSystemParallelThreadPoolSpinning::run(IRunnable* runnable, int num_total_tasks) {
    // NOTE: CS149 students are not expected to implement TaskSystemParallelThreadPoolSpinning in Part B.
    for (int i = 0; i < num_total_tasks; i++) {
        runnable->runTask(i, num_total_tasks);
    }
}

TaskID TaskSystemParallelThreadPoolSpinning::runAsyncWithDeps(IRunnable* runnable, int num_total_tasks,
                                                              const std::vector<TaskID>& deps) {
    // NOTE: CS149 students are not expected to implement TaskSystemParallelThreadPoolSpinning in Part B.
    for (int i = 0; i < num_total_tasks; i++) {
        runnable->runTask(i, num_total_tasks);
    }

    return 0;
}

void TaskSystemParallelThreadPoolSpinning::sync() {
    // NOTE: CS149 students are not expected to implement TaskSystemParallelThreadPoolSpinning in Part B.
    return;
}

/*
 * ================================================================
 * Parallel Thread Pool Sleeping Task System Implementation
 * ================================================================
 */

const char* TaskSystemParallelThreadPoolSleeping::name() {
    return "Parallel + Thread Pool + Sleep";
}

TaskSystemParallelThreadPoolSleeping::TaskSystemParallelThreadPoolSleeping(int num_threads)
    : ITaskSystem(num_threads) 
    , num_threads_(num_threads) 
    , taskID_(0)
    , flag_(true) {
    //
    // TODO: CS149 student implementations may decide to perform setup
    // operations (such as thread pool construction) here.
    // Implementations are free to add new class member variables
    // (requiring changes to tasksys.h).
    //
    worker_ = new std::thread[num_threads];
    for (int i = 0; i < num_threads; i++) {
        worker_[i] = std::thread(&TaskSystemParallelThreadPoolSleeping::thread_fn, this);
    }
}

TaskSystemParallelThreadPoolSleeping::~TaskSystemParallelThreadPoolSleeping() {
    //
    // TODO: CS149 student implementations may decide to perform cleanup
    // operations (such as thread pool shutdown construction) here.
    // Implementations are free to add new class member variables
    // (requiring changes to tasksys.h).
    //
    mutex_.lock();
    flag_ = false;
    mutex_.unlock();
    undone_.notify_all();
    for (int i = 0; i < num_threads_; i++) {
        worker_[i].join();
    }
    delete[] worker_;
}

void TaskSystemParallelThreadPoolSleeping::thread_fn() {
    std::unique_lock<std::mutex> lk;

    IRunnable* runnable;
    int num_left_tasks;
    int num_total_tasks;
    TaskID taskID;

    while (true) {
        lk = std::unique_lock<std::mutex>(mutex_);
        if (!flag_) {
            lk.unlock();
            break;
        }

        if (ready_.empty() && waiting_.empty()) {
            undone_.wait(lk);
        }

        if (ready_.empty() && waiting_.empty()) {
            lk.unlock();
            continue;
        }

        while (!ready_.empty()) {
            auto ready_node = ready_.begin();

            while (ready_node->num_left_tasks_ == 0 && std::next(ready_node) != ready_.end()) {
                ready_node++;
            }

            if (ready_node->num_left_tasks_ == 0 && std::next(ready_node) == ready_.end()) {
                undone_.wait(lk);
                continue;
            }

            runnable = ready_node->runnable_;
            num_left_tasks = ready_node->num_left_tasks_;
            num_total_tasks = ready_node->num_total_tasks_;
            
            if (num_left_tasks != 0) {
                ready_node->num_left_tasks_--;
                ready_node->num_workers_++;
                lk.unlock();
                runnable->runTask(num_left_tasks-1, num_total_tasks);
                lk.lock();
                ready_node->num_workers_--;
            }

            if (ready_node->num_left_tasks_ == 0 && ready_node->num_workers_ == 0 && ready_node != ready_.begin()) {
                for (size_t i = 0; i < ready_node->next_.size(); i++) {
                    auto next_waiting = waiting_map_.find(ready_node->next_[i]);
                    auto next_node = next_waiting->second;
                    next_node->prev_.erase(
                        std::remove(next_node->prev_.begin(), next_node->prev_.end(), ready_node->taskID_),
                        next_node->prev_.end());

                    if (next_node->prev_.empty()) {
                        taskID = next_node->taskID_;
                        auto waiting_value = waiting_map_.find(taskID);
                        ready_.splice(ready_.end(), waiting_, waiting_value->second);
                        ready_map_[taskID] = waiting_value->second;
                        waiting_map_.erase(taskID);
                        undone_.notify_all();
                    }
                }
                ready_map_.erase(ready_node->taskID_);
                ready_.erase(ready_node);
            }


            if (ready_.begin()->num_left_tasks_ == 0 && ready_.begin()->num_workers_ == 0) {
                for (size_t i = 0; i < ready_.begin()->next_.size(); i++) {
                    auto next_waiting = waiting_map_.find(ready_.begin()->next_[i]);
                    auto next_node = next_waiting->second;
                    next_node->prev_.erase(
                        std::remove(next_node->prev_.begin(), next_node->prev_.end(), ready_.begin()->taskID_),
                        next_node->prev_.end());

                    if (next_node->prev_.empty()) {
                        taskID = next_node->taskID_;
                        auto waiting_value = waiting_map_.find(taskID);
                        ready_.splice(ready_.end(), waiting_, waiting_value->second);
                        ready_map_[taskID] = waiting_value->second;
                        waiting_map_.erase(taskID);
                        undone_.notify_all();
                    }
                        
                }
                ready_map_.erase(ready_.begin()->taskID_);
                ready_.pop_front();
            }
        }

        if (ready_.empty() && waiting_.empty()) {
            lk.unlock();
            done_.notify_one();
            continue;
        }
        
        lk.unlock();
    }
}

void TaskSystemParallelThreadPoolSleeping::run(IRunnable* runnable, int num_total_tasks) {


    //
    // TODO: CS149 students will modify the implementation of this
    // method in Parts A and B.  The implementation provided below runs all
    // tasks sequentially on the calling thread.
    //
    if (!runnable || !num_total_tasks)
        return;

    std::unique_lock<std::mutex> lk(mutex_);
    TaskID taskID = taskID_++;

    ready_.push_back({taskID, runnable, num_total_tasks, num_total_tasks, 0});
    ready_map_[taskID] = std::prev(ready_.end());
    lk.unlock();

    undone_.notify_all();

    while (true) {
        lk.lock();
        if (ready_.empty()) {
            lk.unlock();
            break;
        }
        else {
            done_.wait(lk);
        }
        lk.unlock();
    }
}

TaskID TaskSystemParallelThreadPoolSleeping::runAsyncWithDeps(IRunnable* runnable, int num_total_tasks,
                                                    const std::vector<TaskID>& deps) {


    //
    // TODO: CS149 students will implement this method in Part B.
    //

    if (!runnable || !num_total_tasks)
        return -1;

    mutex_.lock();
    TaskID taskID = taskID_++;
    std::vector<TaskID> deps_fn = deps;

    if (deps.empty()) {
        ready_.push_back({taskID, runnable, num_total_tasks, num_total_tasks, 0, deps});
        ready_map_[taskID] = std::prev(ready_.end());
    }
    else {
        for (size_t i = 0; i < deps.size(); i++) {
            auto waiting_value = waiting_map_.find(deps[i]);
            auto ready_value = ready_map_.find(deps[i]);
            if (waiting_value == waiting_map_.end() && ready_value == ready_map_.end()) {
                deps_fn.erase(std::remove(deps_fn.begin(), deps_fn.end(), deps[i]), deps_fn.end());
            }
        }
        if (!deps_fn.empty()) {
            for (size_t i = 0; i < deps_fn.size(); i++) {
                auto prev_waiting = waiting_map_.find(deps_fn[i]);
                auto prev_ready = ready_map_.find(deps_fn[i]);
                if (prev_waiting != waiting_map_.end()) {
                    auto prev_node = prev_waiting->second;
                    prev_node->next_.push_back(taskID);
                }
                else if (prev_ready != ready_map_.end()) {
                    auto prev_node = prev_ready->second;
                    prev_node->next_.push_back(taskID);
                }
            }
            waiting_.push_back({taskID, runnable, num_total_tasks, num_total_tasks, 0, deps_fn});
            waiting_map_[taskID] = std::prev(waiting_.end());
        }
        else {
            ready_.push_back({taskID, runnable, num_total_tasks, num_total_tasks, 0, deps_fn});
            ready_map_[taskID] = std::prev(ready_.end());
        }
    }
    mutex_.unlock();
    undone_.notify_all();

    return taskID;
}

void TaskSystemParallelThreadPoolSleeping::sync() {

    //
    // TODO: CS149 students will modify the implementation of this method in Part B.
    //
    std::unique_lock<std::mutex> lk;
    while (true) {
        lk = std::unique_lock<std::mutex>(mutex_);
        if (ready_.empty() && waiting_.empty()) {
            lk.unlock();
            break;
        }
        else {
            done_.wait(lk);
        }
        lk.unlock();
    }
    
    return;
}
