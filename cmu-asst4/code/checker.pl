#!/usr/bin/perl

use POSIX;
use Getopt::Std;

my @test_names = ("easy", "medium", "hard", "extreme");
my @test_nprocs = (1, 2, 4, 8);


my %fast_times;
$fast_times{"easy"}{1} = 0.49;
$fast_times{"easy"}{2} = 0.31;
$fast_times{"easy"}{4} = 0.19;
$fast_times{"easy"}{8} = 0.13;
$fast_times{"medium"}{1} = 9.52;
$fast_times{"medium"}{2} = 6.12;
$fast_times{"medium"}{4} = 4.04;
$fast_times{"medium"}{8} = 3.41;
$fast_times{"hard"}{1} = 11.15;
$fast_times{"hard"}{2} = 7.08;
$fast_times{"hard"}{4} = 4.1;
$fast_times{"hard"}{8} = 3.1;
$fast_times{"extreme"}{1} = 46.81;
$fast_times{"extreme"}{2} = 28.95;
$fast_times{"extreme"}{4} = 15.2;
$fast_times{"extreme"}{8} = 11;

my $good_costs;
$good_costs{"easy"} = 122050;
$good_costs{"medium"} = 601213;
$good_costs{"hard"} = 1032198;
$good_costs{"extreme"} = 23613045;

my %scores;
$scores{"easy"} = 1;
$scores{"medium"} = 2;
$scores{"hard"} = 3;
$scores{"extreme"} = 4;

my $perf_points = 10;
my $min_perf_points = 1;
my $min_ratio = 0.1;
my $max_ratio = 5.0/6.0;
my $max_ratio_cost = 9.0 / 10.0;

my %correct;

my %your_times;
my %your_costs;

sub usage {
    printf STDERR "$_[0]";
    printf STDERR "Usage: $0 [-h] [-R] [-s SIZE]\n";
    printf STDERR "    -h         Print this message\n";
    printf STDERR "    -R         Use reference (CPU-based) renderer\n";
    printf STDERR "    -s SIZE    Set image size\n";
    die "\n";
}

getopts('hRs:');
if ($opt_h) {
    usage();
}

`mkdir -p logs`;
`rm -rf logs/*`;

print "\n";
print ("--------------\n");
my $hostname = `hostname`;
chomp $hostname;
print ("Running tests on $hostname\n");
print ("--------------\n");

foreach my $test (@test_names) {
    foreach my $nproc (@test_nprocs) {
        print ("\nTest : $test with $nproc cores\n");
        my @sys_stdout = system ("mpirun -np ${nproc} ./wireroute -f ./inputs/timeinput/${test}_4096.txt -p 0.1 -i 5 -b 8 -m A > ./logs/${test}_${nproc}.log");
        my $return_value  = $?;
        if ($return_value == 0) {
            print ("Correctness passed!\n");
            $correct{$test}{$nproc} = 1;
        }
        else {
            print ("Correctness failed ... Check ./logs/${test}_${nproc}.log\n");
            $correct{$test}{$nproc} = 0;
        }
        
        my $your_time = `grep Computation ./logs/${test}_${nproc}.log`;
        chomp($your_time);
        $your_time =~ s/^[^0-9]*//;
        $your_time =~ s/ ms.*//;

        print ("Your time : $your_time\n");
        $your_times{$test}{$nproc} = $your_time;

        $target = $fast_times{$test}{$nproc};
        print ("Target Time: $target\n");

        my $your_cost = `grep cost ./logs/${test}_${nproc}.log`;
        chomp($your_cost);
        $your_cost =~ s/^[^0-9]*//;
        $your_cost =~ s/ ms.*//;
        print ("Your cost : $your_cost\n");
        $your_costs{$test}{$nproc} = $your_cost;
        
        $target_cost = $good_costs{$test};
        print ("Target Cost: $target_cost\n");
        
    }
}

print "\n";
print ("------------\n");
print ("Score table:\n");
print ("------------\n");

my $header = sprintf ("| %-18s | %-18s | %-18s | %-18s | %-18s | %-18s | %-18s |\n", "Test Name", "Core Num", "Target Time ", "Your Time", "Target Cost", "Your Cost", "Score");
my $dashes = $header;
$dashes =~ s/./-/g;
print $dashes;
print $header;
print $dashes;

my $total_score = 0;

foreach my $test (@test_names) {
    foreach my $nproc (@test_nprocs) {
        my $score;
        my $your_time = $your_times{$test}{$nproc};
        my $your_cost = $your_costs{$test}{$nproc};
        my $fast_time = $fast_times{$test}{$nproc};
        my $good_cost = $good_costs{$test};
        my $cost_score;
        my $time_score;
    
        if ($correct{$test}{$nproc}) {
    	      $ratio = $fast_time/$your_time;
              $cost_ratio = $good_cost/$your_cost;
            if ($ratio >= $max_ratio) {
                if ($cost_ratio >= $max_ratio_cost) {
                    $score = $scores{$test};
                } else {
                    $score = $scores{$test} * $cost_ratio;
                }
                
            }
            else {
                if ($cost_ratio >= $max_ratio_cost) {
                    $score = $scores{$test} * $ratio;
                } else {
                    $cost_score = $scores{$test} * $cost_ratio;
                    $time_score = $scores{$test} * $ratio;
                    if ($cost_score > $time_score) {
                        $score = $time_score
                    } else {
                        $score = $cost_score
                    }
                }
                
            }
        }
        else {
            $your_time .= " (F)";
            $score = 0;
        }
    
        printf ("| %-18s | %-18s | %-18s | %-18s | %-18s | %-18s | %-18s |\n", "$test", "$nproc", "$fast_time", "$your_time","$good_cost", "$your_cost", "$score");
        $total_score += $score;
    }
}
print $dashes;
printf ("| %-18s   %-18s   %-18s  %-18s   %-18s | %-18s | %-18s |\n", "", "","", "", "", "Total score:",
    $total_score . "/" . 40);
print $dashes;
