# cybergym-patch-bug

An [OpenEnv](https://github.com/meta-pytorch/OpenEnv) cyber environment for
[OpenEnv Arena: CyberGym](https://openenvarena-cybergym.hf.space): six
defensive-fixing tasks. Each task ships a small Python module with a bug whose
public tests still pass; the hidden tests encode the specification the bug
breaks. The submitted module source is imported and graded server-side —
public and hidden tests must all pass.

- Action schema: `cmd` (shell command in the task folder; run the public tests,
  experiment) and `answer` (the full corrected module source; ends the episode).
- Reward 1.0 when every public and hidden test passes on the submission.

## Tasks

| task_id | bug class |
|---|---|
| sum-upto | boundary condition |
| average-float | integer division |
| clip-upper | missing upper clamp |
| parse-kv | wrong split |
| count-vowels | incomplete alphabet |
| rotate-left | aliasing / missing modulo |

## Licence

BSD-3-Clause, following OpenEnv.
