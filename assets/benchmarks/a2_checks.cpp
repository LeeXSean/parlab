// Standalone Part B checks; compile against the student's tasksys.cpp.
#include "tasksys.h"
#include <atomic>
#include <chrono>
#include <iostream>
#include <memory>
#include <random>
#include <thread>
#include <vector>

struct CheckedWork : IRunnable {
    std::atomic<int> completed{0};
    std::vector<CheckedWork*> predecessors;
    std::unique_ptr<std::atomic<int>[]> seen;
    const int count;
    const bool pause;
    std::atomic<bool>& failed;

    CheckedWork(int n, bool delay, std::atomic<bool>& error)
        : seen(new std::atomic<int>[n]), count(n), pause(delay), failed(error) {
        for (int i = 0; i < count; ++i) seen[i] = 0;
    }

    void runTask(int id, int total) override {
        if (total != count || id < 0 || id >= count) {
            failed = true;
            return;
        }
        for (auto* predecessor : predecessors) {
            if (predecessor->completed.load() != predecessor->count) failed = true;
        }
        if (seen[id].fetch_add(1) != 0) failed = true;
        if (pause) std::this_thread::sleep_for(std::chrono::microseconds(100));
        else if (id % 2 == 0) std::this_thread::yield();
        completed.fetch_add(1);
    }

    bool correct() const {
        if (completed.load() != count) return false;
        for (int i = 0; i < count; ++i) if (seen[i].load() != 1) return false;
        return true;
    }
};

int main() {
    std::atomic<bool> failed(false);
    for (int threads : {1, 2, 8}) {
        TaskSystemParallelThreadPoolSleeping pool(threads);
        for (int trial = 0; trial < 300; ++trial) {
            CheckedWork a(1, true, failed), b(1, false, failed);
            b.predecessors.push_back(&a);
            TaskID aid = pool.runAsyncWithDeps(&a, 1, {});
            pool.runAsyncWithDeps(&b, 1, {aid});
            pool.sync();
            if (failed || !a.correct() || !b.correct()) return 1;
        }
        std::mt19937 random(20261014);
        for (int trial = 0; trial < 50; ++trial) {
            std::vector<std::unique_ptr<CheckedWork>> work;
            std::vector<TaskID> ids;
            for (int i = 0; i < 48; ++i) {
                work.emplace_back(new CheckedWork(1 + random() % 7, i % 13 == 0, failed));
                std::vector<TaskID> deps;
                for (int j = 0; j < i; ++j) {
                    if (j == i - 1 || random() % 17 == 0) {
                        deps.push_back(ids[j]);
                        work.back()->predecessors.push_back(work[j].get());
                    }
                }
                ids.push_back(pool.runAsyncWithDeps(work.back().get(), work.back()->count, deps));
            }
            pool.sync();
            if (failed) return 2;
            for (const auto& launch : work) if (!launch->correct()) return 3;
            pool.sync();
        }
        std::cout << "PASS n=" << threads
                  << ": 300 A->B rounds and 50 DAG rounds\n";
    }
    for (int i = 0; i < 30; ++i) {
        TaskSystemParallelThreadPoolSleeping pool(8);
        pool.sync();
    }
    std::cout << "PASS idle construction/destruction x30\n";
}
