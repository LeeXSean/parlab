#!/bin/bash

files_to_remove=(
    ".ninja_log"
    ".ninja_deps"
    "build.ninja"
    "submission_cuda.so"
    "cuda.cu"
    "cuda.cuda.o"
    "main.cpp"
    "main.o"
)

for file in "${files_to_remove[@]}"; do
    rm -rf $file
done
