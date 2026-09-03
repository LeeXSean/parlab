#include "sqrt3.h"
#include "mpi.h"
#include <math.h>
#include <stdio.h>

// Approximate sqrt(3) with different starting conditions
float approxSqrt3(float x) {
  int i;
  for (i = 0; i < 10000000; i++) {
    x = 1.0 - (0.5 * x * x);
  }
  return x + 1.0;
}

// Perform computation
void compute(int procID, int nproc) {
  const int root = 0; // Set the rank 0 process as the root process
  int tag = 0;        // Use the same tag
  MPI_Status status;
  int source;

  const int numIterations = 240; // Total number of iterations
  int iterationIndex;
  int startIndex;
  int endIndex;
  int span;
  float *inputs;
  float *outputs;
  float sqrt3;

  inputs = new float[numIterations];
  outputs = new float[numIterations];

  // Initialize inputs
  if (procID == root) {
    for (iterationIndex = 0; iterationIndex < numIterations; iterationIndex++) {
      inputs[iterationIndex] = 1.0 / (1.0 + iterationIndex);
    }
  }

  // Broadcast the array of inputs to all processes
  MPI_Bcast(inputs, numIterations, MPI_FLOAT, root, MPI_COMM_WORLD);

  // Compute sqrt(3)
  span = (numIterations + nproc - 1) / nproc;
  startIndex = procID * span;
  endIndex = min(numIterations, startIndex + span);
  for (iterationIndex = startIndex; iterationIndex < endIndex;
       iterationIndex++) {
    outputs[iterationIndex] = approxSqrt3(inputs[iterationIndex]);
  }

  // Send data to root process
  if (procID != root) {
    MPI_Send(&outputs[startIndex], endIndex - startIndex, MPI_FLOAT, root, tag,
             MPI_COMM_WORLD);
  } else {
    for (source = 1; source < nproc; source++) {
      startIndex = source * span;
      endIndex = min(numIterations, startIndex + span);
      MPI_Recv(&outputs[startIndex], endIndex - startIndex, MPI_FLOAT, source,
               tag, MPI_COMM_WORLD, &status);
    }
  }

  // Validate results
  if (procID == root) {
    sqrt3 = sqrt(3);
    for (iterationIndex = 0; iterationIndex < numIterations; iterationIndex++) {
      if (!approxEqual(sqrt3, outputs[iterationIndex])) {
        printf("Computation error\n");
      }
    }
  }

  delete[] inputs;
  delete[] outputs;
}
