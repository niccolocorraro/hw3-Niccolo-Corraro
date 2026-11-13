15 query con almeno un documento rilevante, k = 10

| Run | P@10 | R@10 | F1@10 | MRR | Giudicati@10 |
| --- | --- | --- | --- | --- | --- |
| content_whitespace_bm25 | 0.280 | 0.324 | 0.262 | 0.596 | 0.627 |
| content_leggero_bm25 | 0.420 | 0.465 | 0.391 | 0.646 | 1.000 |
| content_italian_bm25 | 0.520 | 0.564 | 0.484 | 0.735 | 1.000 |
| content_italian_classic | 0.413 | 0.453 | 0.384 | 0.556 | 1.000 |
| content_italian_lmdirichlet | 0.440 | 0.507 | 0.420 | 0.766 | 1.000 |
| content_italian_constant | 0.007 | 0.004 | 0.005 | 0.017 | 0.013 |
| content_italian_bm25_and | 0.520 | 0.564 | 0.484 | 0.735 | 1.000 |
