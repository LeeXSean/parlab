#include "mpi.h"
#include "sqrt3.h"
#include <stdio.h>

int main(int argc, char *argv[]) {
  int procID;
  int nproc;
  double startTime;
  double endTime;

  // Initialize MPI
  MPI_Init(&argc, &argv);

  // Get process rank
  MPI_Comm_rank(MPI_COMM_WORLD, &procID);

  // Get total number of processes specificed at start of run
  MPI_Comm_size(MPI_COMM_WORLD, &nproc);

  // Run computation
  startTime = MPI_Wtime();
  compute(procID, nproc);
  endTime = MPI_Wtime();

  // Compute running time
  MPI_Finalize();
  printf("elapsed time for proc %d: %f\n", procID, endTime - startTime);
  return 0;
}
