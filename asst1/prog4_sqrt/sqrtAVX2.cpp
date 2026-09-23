#include <immintrin.h>
#include <climits>

void sqrtAVX2(int N,
                float initialGuess,
                float values[],
                float output[])
{
    static const __m256 kThreshold = _mm256_set1_ps(0.00001f);

    __m256 x;
    __m256 guess1;
    __m256 guess2;
    __m256 guess3;
    __m256 error;

    for (int i=0; i<N; i+=8) {

        x = _mm256_loadu_ps(values+i);
        guess1 = _mm256_set1_ps(initialGuess);

        guess2 = _mm256_mul_ps(guess1, guess1);
        error = _mm256_fmsub_ps(guess2, x, _mm256_set1_ps(1.f));
        error = _mm256_and_ps(error, _mm256_castsi256_ps(_mm256_set1_epi32(INT_MAX)));

        while (_mm256_movemask_ps(_mm256_cmp_ps(error, kThreshold, _CMP_GT_OQ))) {
            guess3 = _mm256_mul_ps(guess2, guess1);
            guess1 = _mm256_sub_ps(_mm256_mul_ps(_mm256_set1_ps(3.f), guess1), _mm256_mul_ps(x, guess3));
            guess1 = _mm256_mul_ps(guess1, _mm256_set1_ps(0.5f));
            guess2 = _mm256_mul_ps(guess1, guess1);
            error = _mm256_fmsub_ps(guess2, x, _mm256_set1_ps(1.f));
            error = _mm256_and_ps(error, _mm256_castsi256_ps(_mm256_set1_epi32(INT_MAX)));
        }

        _mm256_storeu_ps(output+i, _mm256_mul_ps(x, guess1));
    }
}
