/*
ID: math4to3
LANG: C++
TASK: ariprog
*/
#include <iostream>
#include <fstream>
#include <vector>
#include <utility>
#include <algorithm>
using namespace std;

long square(long x) {
  return x * x;
}

bool check(long N, long a, long diff, vector<bool> &sieve) {
  for (long i = 0; i < N; i++) {
    long x = a + i * diff;
    if (x >= sieve.size() || !sieve[x]) {
      return false;
    }
  }
  return true;
}

vector<pair<long, long> > solve(long N, long M) {
  vector<pair<long, long> > ret;
  vector<bool> sieve(square(M) * 2 + 1, false);
  for (long p = 0; p <= M; p++) {
    for (long q = 0; q <= M; q++) {
      sieve[square(p) + square(q)] = true;
    }
  }
  vector<long> bisquares;
  for (long i = 0; i < sieve.size(); i++) {
    if (sieve[i]) {
      bisquares.push_back(i);
    }
  }
  for (long i = 0; i < bisquares.size(); i++) {
    long bisquare_i = bisquares[i];
    for (long j = i + 1; j < bisquares.size(); j++) {
      long diff = bisquares[j] - bisquares[i];
      if (check(N, bisquare_i, diff, sieve)) {
        ret.push_back(make_pair(diff, bisquare_i));
      }
    }
  }
  sort(ret.begin(), ret.end());
  return ret;
}

int main() {
  ifstream fin("ariprog.in");
  ofstream fout("ariprog.out");

  long N, M;
  fin >> N >> M;

  vector<pair<long, long> > pairs = solve(N, M);

  if (pairs.size()) {
    for (long i = 0; i < pairs.size(); i++) {
      fout << pairs[i].second << " " << pairs[i].first << endl;
    }
  } else {
    fout << "NONE" << endl;
  }
}
