APP_NAME=tutorial

CXX = mpic++
CXXFLAGS = -Wall -Wextra -O3 -std=c++20 -I.

OBJS := sqrt3.o main.o
all: $(APP_NAME)
$(APP_NAME): $(OBJS)

$(APP_NAME): $(OBJS)
	$(CXX) $(CXXFLAGS) -o $@ $(OBJS)

%.o: %.c
	$(CXX) $< $(CXXFLAGS) -c -o $@

clean:
	/bin/rm -rf *~ *.o $(APP_NAME)
