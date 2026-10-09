/* STATUS: DRAFT - UNVERIFIED - requires human review at Gate G3
 * SPDX-License-Identifier: MIT
 *
 * Grid A* for tools/pcb/finisher.py (compiled on first use with the system C compiler; finisher.py falls back to
 * its Python search if that fails). Layers x nx x ny cells. cost[l][i][j] < 0: blocked; otherwise added to the step
 * length (a "soft" cell: crossing another net's track that the caller may rip up). via[i][j] < 0: no via here;
 * otherwise added to the via cost. 8-neighbour moves, no corner cutting. h = weight * distance to the nearest of
 * the sampled goal points.
 */
#include <math.h>
#include <stdlib.h>

typedef struct { float f; int n; } item;

static void push(item *h, int *len, float f, int n) {
    int k = (*len)++;
    while (k > 0) {
        int p = (k - 1) / 2;
        if (h[p].f <= f) break;
        h[k] = h[p];
        k = p;
    }
    h[k].f = f; h[k].n = n;
}

static item pop(item *h, int *len) {
    item top = h[0], last = h[--(*len)];
    int k = 0;
    for (;;) {
        int c = 2 * k + 1;
        if (c >= *len) break;
        if (c + 1 < *len && h[c + 1].f < h[c].f) c++;
        if (h[c].f >= last.f) break;
        h[k] = h[c];
        k = c;
    }
    h[k] = last;
    return top;
}

int astar(int nl, int nx, int ny, const float *cost, const float *via, const unsigned char *start,
          const unsigned char *goal, const int *gpts, int ng, float res, float via_base, float weight,
          long limit, int *path, int maxpath) {
    long N = (long)nl * nx * ny, NN = (long)nx * ny;
    float *g = malloc(N * sizeof(float));
    int *par = malloc(N * sizeof(int));
    unsigned char *done = calloc(N, 1);
    long cap = N * 4 + 16;
    item *heap = malloc(cap * sizeof(item));
    int len = 0, end = -1;
    if (!g || !par || !done || !heap) { free(g); free(par); free(done); free(heap); return -2; }
    for (long k = 0; k < N; k++) { g[k] = 1e30f; par[k] = -1; }
#define H(i, j) ({ float best = 1e30f; for (int q = 0; q < ng; q++) { float dx = (float)(gpts[2*q] - (i)), dy = (float)(gpts[2*q+1] - (j)); float d = dx*dx + dy*dy; if (d < best) best = d; } weight * sqrtf(best) * res; })
    for (long k = 0; k < N; k++) {
        if (start[k] && cost[k] >= 0) {
            int i = (k % NN) / ny, j = k % ny;
            g[k] = 0; push(heap, &len, H(i, j), (int)k);
        }
    }
    static const int di[8] = {1, -1, 0, 0, 1, 1, -1, -1}, dj[8] = {0, 0, 1, -1, 1, -1, 1, -1};
    while (len > 0 && limit-- > 0) {
        item it = pop(heap, &len);
        int n = it.n;
        if (done[n]) continue;
        done[n] = 1;
        if (goal[n]) { end = n; break; }
        int L = n / NN, i = (n % NN) / ny, j = n % ny;
        float gn = g[n];
        for (int d = 0; d < 8; d++) {
            int a = i + di[d], c = j + dj[d];
            if (a < 0 || a >= nx || c < 0 || c >= ny) continue;
            long m = (long)L * NN + (long)a * ny + c;
            if (cost[m] < 0 || done[m]) continue;
            if (di[d] && dj[d]) {
                if (cost[(long)L * NN + (long)(i + di[d]) * ny + j] < 0 || cost[(long)L * NN + (long)i * ny + j + dj[d]] < 0) continue;
            }
            float step = res * ((di[d] && dj[d]) ? 1.41421356f : 1.0f) + cost[m];
            float nd = gn + step;
            if (nd < g[m]) {
                g[m] = nd; par[m] = n;
                if (len >= cap - 1) { cap *= 2; heap = realloc(heap, cap * sizeof(item)); }
                push(heap, &len, nd + H(a, c), (int)m);
            }
        }
        float vc = via[(long)i * ny + j];
        if (vc >= 0) {
            for (int L2 = 0; L2 < nl; L2++) {
                if (L2 == L) continue;
                long m = (long)L2 * NN + (long)i * ny + j;
                if (cost[m] < 0 || done[m]) continue;
                float nd = gn + via_base + vc + cost[m];
                if (nd < g[m]) {
                    g[m] = nd; par[m] = n;
                    if (len >= cap - 1) { cap *= 2; heap = realloc(heap, cap * sizeof(item)); }
                    push(heap, &len, nd + H(i, j), (int)m);
                }
            }
        }
    }
    int count = -1;
    if (end >= 0) {
        count = 0;
        for (int n = end; n >= 0 && count < maxpath; n = par[n]) path[count++] = n;
    }
    free(g); free(par); free(done); free(heap);
    return count;
}
