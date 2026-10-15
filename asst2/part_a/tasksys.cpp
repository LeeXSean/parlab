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
    // You do not need to implement this method.
    return 0;
}

void TaskSystemSerial::sync() {
    // You do not need to implement this method.
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

TaskSystemParallelSpawn::TaskSystemParallelSpawn(int num_threads)
    : ITaskSystem(num_threads) 
    , num_threads_(num_threads) 
    , num_workers_(0)
    , num_total_tasks_(0)
    , num_left_tasks_(0)
    , runnable_(nullptr){
    //
    // TODO: CS149 student implementations may decide to perform setup
    // operations (such as thread pool construction) here.
    // Implementations are free to add new class member variables
    // (requiring changes to tasksys.h).
    //
    mutex_ = new std::mutex();
}

TaskSystemParallelSpawn::~TaskSystemParallelSpawn() {
    delete mutex_;
}

void TaskSystemParallelSpawn::thread_fn() {
    int num_left_tasks;
    int num_total_tasks;
    while (true) {   
        mutex_->lock();
        if (!runnable_ || num_left_tasks_ == 0) {
            mutex_->unlock();
            break;
        }
        
        if (runnable_ && num_left_tasks_ != 0) {
            num_left_tasks = num_left_tasks_;
            num_total_tasks = num_total_tasks_;
            num_left_tasks_--;
            num_workers_++;
            mutex_->unlock();
            runnable_->runTask(num_left_tasks-1, num_total_tasks);
            mutex_->lock();
            num_workers_--;
        }

        mutex_->unlock();
    }
}

void TaskSystemParallelSpawn::run(IRunnable* runnable, int num_total_tasks) {


    //
    // TODO: CS149 students will modify the implementation of this
    // method in Part A.  The implementation provided below runs all
    // tasks sequentially on the calling thread.
    //

    if (!runnable || !num_total_tasks)
        return;
    
    std::thread* worker = new std::thread[num_threads_];
    num_total_tasks_ = num_total_tasks;
    num_left_tasks_ = num_total_tasks;
    runnable_ = runnable;

    for (int i = 0; i < num_threads_; i++) {
        worker[i] = std::thread(&TaskSystemParallelSpawn::thread_fn, this);
    }
    
    while (true) {
        mutex_->lock();
        if (num_left_tasks_ == 0 && num_workers_ == 0) {
            runnable_ = nullptr;
            mutex_->unlock();
            for (int i = 0; i < num_threads_; i++) {
                worker[i].join();
            }
            break;
        }
        mutex_->unlock();
    }
    

    delete[] worker;
}

TaskID TaskSystemParallelSpawn::runAsyncWithDeps(IRunnable* runnable, int num_total_tasks,
                                                 const std::vector<TaskID>& deps) {
    // You do not need to implement this method.
    return 0;
}

void TaskSystemParallelSpawn::sync() {
    // You do not need to implement this method.
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

TaskSystemParallelThreadPoolSpinning::TaskSystemParallelThreadPoolSpinning(int num_threads)
    : ITaskSystem(num_threads) 
    , num_threads_(num_threads) 
    , num_workers_(0)
    , num_total_tasks_(0)
    , num_left_tasks_(0)
    , flag_(true) 
    , runnable_(nullptr) {
    //
    // TODO: CS149 student implementations may decide to perform setup
    // operations (such as thread pool construction) here.
    // Implementations are free to add new class member variables
    // (requiring changes to tasksys.h).
    //
    mutex_ = new std::mutex();
    worker_ = new std::thread[num_threads];
    for (int i = 0; i < num_threads; i++) {
        worker_[i] = std::thread(&TaskSystemParallelThreadPoolSpinning::thread_fn, this);
    }
}

TaskSystemParallelThreadPoolSpinning::~TaskSystemParallelThreadPoolSpinning() { 
    mutex_->lock();
    flag_ = false;
    mutex_->unlock();
    for (int i = 0; i < num_threads_; i++) {
        worker_[i].join();
    }
    delete[] worker_;
    delete mutex_;
}

void TaskSystemParallelThreadPoolSpinning::thread_fn() {
    int num_left_tasks;
    int num_total_tasks;
    while (true) {    
        mutex_->lock();
        if (!flag_) {
            mutex_->unlock();
            break;
        }
        
        while (runnable_ && num_left_tasks_ != 0) {
            num_left_tasks = num_left_tasks_;
            num_total_tasks = num_total_tasks_;
            num_left_tasks_--;
            num_workers_++;
            mutex_->unlock();
            runnable_->runTask(num_left_tasks-1, num_total_tasks);
            mutex_->lock();
            num_workers_--;
        }
        mutex_->unlock();
    }
}

void TaskSystemParallelThreadPoolSpinning::run(IRunnable* runnable, int num_total_tasks) {


    //
    // TODO: CS149 students will modify the implementation of this
    // method in Part A.  The implementation provided below runs all
    // tasks sequentially on the calling thread.
    //

    if (!runnable || !num_total_tasks)
        return;

    mutex_->lock();
    num_total_tasks_ = num_total_tasks;
    num_left_tasks_ = num_total_tasks;
    runnable_ = runnable;
    mutex_->unlock();

    while (runnable_) {
        mutex_->lock();
        if (num_left_tasks_ == 0 && num_workers_ == 0) {
            runnable_ = nullptr;
        }
        mutex_->unlock();
    }
    
}

TaskID TaskSystemParallelThreadPoolSpinning::runAsyncWithDeps(IRunnable* runnable, int num_total_tasks,
                                                              const std::vector<TaskID>& deps) {
    // You do not need to implement this method.
    return 0;
}

void TaskSystemParallelThreadPoolSpinning::sync() {
    // You do not need to implement this method.
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
    , num_workers_(0)
    , num_total_tasks_(0)
    , num_left_tasks_(0)
    , flag_(true) 
    , runnable_(nullptr) {
    //
    // TODO: CS149 student implementations may decide to perform setup
    // operations (such as thread pool construction) here.
    // Implementations are free to add new class member variables
    // (requiring changes to tasksys.h).
    //
    undone_ = new std::condition_variable();
    done_ = new std::condition_variable();
    mutex_ = new std::mutex();
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
    mutex_->lock();
    flag_ = false;
    mutex_->unlock();
    undone_->notify_all();
    for (int i = 0; i < num_threads_; i++) {
        worker_[i].join();
    }
    delete[] worker_;
    delete mutex_;
    delete undone_;
    delete done_;
}

void TaskSystemParallelThreadPoolSleeping::thread_fn() {
    std::unique_lock<std::mutex> lk;
    int num_left_tasks;
    int num_total_tasks;
    while (true) {
        lk = std::unique_lock<std::mutex>(*mutex_);
        if (!flag_) {
            lk.unlock();
            break;
        }

        if (!runnable_ || num_left_tasks_ == 0) {
            undone_->wait(lk);
        }
        
        while (runnable_ && num_left_tasks_ != 0) {
            num_left_tasks = num_left_tasks_;
            num_total_tasks = num_total_tasks_;
            num_left_tasks_--;
            num_workers_++;
            lk.unlock();
            runnable_->runTask(num_left_tasks-1, num_total_tasks);
            lk.lock();
            num_workers_--;
            if (num_left_tasks_ == 0) {
                if (num_workers_ == 0)
                    break;
                undone_->wait(lk);
            }
        }

        lk.unlock();
        done_->notify_one();
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
        
    std::unique_lock<std::mutex> lk(*mutex_);
    num_total_tasks_ = num_total_tasks;
    num_left_tasks_ = num_total_tasks;
    runnable_ = runnable;
    num_workers_ = 0;
    lk.unlock();

    undone_->notify_all();

    while (runnable_) {
        lk.lock();
        if (num_left_tasks_ == 0 && num_workers_ == 0) {
            runnable_ = nullptr;
        }
        else {
            done_->wait(lk);
        }
        lk.unlock();
    }
}

TaskID TaskSystemParallelThreadPoolSleeping::runAsyncWithDeps(IRunnable* runnable, int num_total_tasks,
                                                    const std::vector<TaskID>& deps) {


    //
    // TODO: CS149 students will implement this method in Part B.
    //

    return 0;
}

void TaskSystemParallelThreadPoolSleeping::sync() {

    //
    // TODO: CS149 students will modify the implementation of this method in Part B.
    //

    return;
}
