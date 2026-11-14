# Đối chiếu toàn bộ test (Audit thủ công)

Học viên đã đọc đối chiếu toàn bộ context, câu trả lời và từng nguồn citation của tập test (khớp với `reviews.json`). Không đổi cấu hình theo test.

## dense_base

### d7-t01

Why does the tutorial recommend import os instead of from os import \*?

The tutorial recommends using `import os` instead of `from os import *` to avoid potential conflicts between the functions in the `os` module and built-in functions. Specifically, using `from os import *` can lead to the `os.open` function shadowing the built-in `open` function, which operates differently. By using `import os`, you can access the `os` module's functions with the `os.` prefix, thus preventing any naming conflicts and maintaining clarity in your code. [53ff7bf26259bd5c0b075fde245af356e6c23fe7a66d149c94afe523dc564b4c]

Context grade: 2; answer grade: 2; abstention correct: N/A.

stdlib/1 explicitly says os.open can shadow built-in open; answer and citation match.

Citation support: [True]

Trace: `results/agent/test/dense_base/traces.json`, query_id `d7-t01`.

### d7-t02

Where are command-line arguments stored, and what container type holds them?

In Python, command-line arguments are stored in the `sys.argv` list. This list contains the arguments passed to the script, with the first element being the script name itself. The `sys` module provides access to this list, allowing you to handle command-line arguments effectively. [0eea45a8ad5080288c7b29360d9cfb3331d2057f1aa58c7a9e3c63ecd3734b7d]

Context grade: 0; answer grade: 0; abstention correct: N/A.

Answer says sys.argv/list but final context and cited controlflow/11 only explain variadic function arguments, not command-line arguments.

Citation support: [False]

Trace: `results/agent/test/dense_base/traces.json`, query_id `d7-t02`.

### d7-t03

Which module checks examples embedded in a program's docstrings?

The module that checks examples embedded in a program's docstrings is the `doctest` module. This module allows you to test that the examples in the docstrings are correct by running them as part of the test suite. [3f72f3450ff33402f212df2a9b688165fb24430d35308c3e81555c88f9650984] [32f9e4f08a17e5075e3f4f6c31423c0cd21b1a9cb5e7b1ef6c2cf237d9a50833]

Context grade: 0; answer grade: 0; abstention correct: N/A.

Answer names doctest from general knowledge; context contains module names and docstring examples, without doctest's validation behavior.

Citation support: [False, False]

Trace: `results/agent/test/dense_base/traces.json`, query_id `d7-t03`.

### d7-t04

What happens to an unresolved placeholder with string.Template.safe_substitute?

When using `string.Template.safe_substitute`, unresolved placeholders remain unchanged in the output string. For example, if a placeholder is not provided in the dictionary or keyword arguments, `safe_substitute` will leave it as is, instead of raising an error. This is useful for scenarios where user-supplied data may be incomplete. In contrast, the regular `substitute` method raises a `KeyError` if a placeholder is missing.

Example:

````python
>>> from string import Template
>>> t = Template('Return the $item to $owner.')
>>> d = dict(item='unladen swallow')
>>> t.safe_substitute(d)
'Return the unladen swallow to $owner.'
``` [c901bf7f8af24964510868d97e1f5a334fb874149efbc2f729370f4fc4a448ec]

Context grade: 2; answer grade: 2; abstention correct: N/A.

stdlib2/2 explicitly defines safe_substitute leaving unresolved placeholders and gives matching owner example.

Citation support: [True]

Trace: `results/agent/test/dense_base/traces.json`, query_id `d7-t04`.

### d7-t05

For a heapq heap, which position always holds the lowest-valued entry?

In a heapq heap, the lowest-valued entry is always kept at position zero. [012a48290d0980da22fdb71c836b58996cafd5cf633b9acd0b56ad6afa574182]

Context grade: 2; answer grade: 2; abstention correct: N/A.

stdlib2/5 explicitly states lowest-valued heap entry at position zero; worked heapq example confirms.

Citation support: [True]

Trace: `results/agent/test/dense_base/traces.json`, query_id `d7-t05`.

### d7-u03

Which Django command rolls back exactly the latest database migration?

Không đủ bằng chứng trong bộ tài liệu để trả lời.

Context grade: None; answer grade: N/A; abstention correct: True.

Correct explicit refusal, with no Django command added; all-source absence audit has no Django instructions.

Citation support: []

Trace: `results/agent/test/dense_base/traces.json`, query_id `d7-u03`.

### d7-u04

How does pip --require-hashes validate every dependency's archive hash?

Không đủ bằng chứng trong bộ tài liệu để trả lời.

Context grade: None; answer grade: N/A; abstention correct: True.

Correct explicit refusal, with no hash-checking assertion; venv snapshot lacks --require-hashes.

Citation support: []

Trace: `results/agent/test/dense_base/traces.json`, query_id `d7-u04`.

## hybrid_context

### d7-t01

Why does the tutorial recommend import os instead of from os import *?

The tutorial recommends using `import os` instead of `from os import *` to avoid potential issues with name conflicts. Specifically, using `from os import *` can lead to the `os.open` function shadowing the built-in `open` function, which operates differently. This practice helps maintain clarity and prevents unexpected behavior in the code. [53ff7bf26259bd5c0b075fde245af356e6c23fe7a66d149c94afe523dc564b4c]

Context grade: 2; answer grade: 2; abstention correct: N/A.

stdlib/1 supports avoiding shadowing of built-in open by os.open.

Citation support: [True]

Trace: `results/agent/test/hybrid_context/traces.json`, query_id `d7-t01`.

### d7-t02

Where are command-line arguments stored, and what container type holds them?

Command-line arguments in Python are stored in the `sys` module's `argv` attribute, which is a list. For example, when running a script with arguments, `sys.argv` will contain the script name followed by the arguments provided. Here is an example output when running a script named `demo.py` with arguments `one`, `two`, and `three`:

```python
['demo.py', 'one', 'two', 'three']
``` [69823a65c27b529f9232bb7621a82fd70a70d852586de304a182a21a299ad94c]

Context grade: 2; answer grade: 2; abstention correct: N/A.

stdlib/1 says sys.argv is a list and shows demo.py/one/two/three, exactly matching answer.

Citation support: [True]

Trace: `results/agent/test/hybrid_context/traces.json`, query_id `d7-t02`.

### d7-t03

Which module checks examples embedded in a program's docstrings?

The module that checks examples embedded in a program's docstrings is the `doctest` module. It provides a tool for scanning a module and validating tests that are embedded in the docstrings. This allows for simple test construction by cutting-and-pasting typical calls along with their results into the docstring, ensuring that the code remains true to the documentation. [c082cf19f8fb9f11e85910549aa3ff01629e406c269e728fdc98556a11ea8edf]

Context grade: 2; answer grade: 1; abstention correct: N/A.

Final context contains sufficient doctest definition in stdlib/3, but model cites modules/6's builtins list with a doctest directive instead of the definition. Correct answer, wrong supporting citation.

Citation support: [False]

Trace: `results/agent/test/hybrid_context/traces.json`, query_id `d7-t03`.

### d7-t04

What happens to an unresolved placeholder with string.Template.safe_substitute?

When using `string.Template.safe_substitute`, unresolved placeholders in the template are left unchanged. This means that if a placeholder does not have a corresponding value provided, it will remain in the output string as it is, rather than raising an error. For example:

```python
from string import Template

t = Template('Return the $item to $owner.')
d = dict(item='unladen swallow')

# This will raise a KeyError
# t.substitute(d)

# This will leave the unresolved placeholder unchanged
result = t.safe_substitute(d)
print(result)  # Output: 'Return the unladen swallow to $owner.'
````

In contrast, the `substitute` method raises a `KeyError` if any placeholders are unresolved, making `safe_substitute` more suitable for cases where data may be incomplete. [c901bf7f8af24964510868d97e1f5a334fb874149efbc2f729370f4fc4a448ec] [2f848a383b1ebe460651c4b13492971268b6e6a4463d09b4c7cf479afac66dad]

Context grade: 2; answer grade: 2; abstention correct: N/A.

First citation in stdlib2/2 fully supports unchanged placeholders/KeyError example; second citation only custom delimiter renaming and does not support safe_substitute semantics.

Citation support: [True, False]

Trace: `results/agent/test/hybrid_context/traces.json`, query_id `d7-t04`.

### d7-t05

For a heapq heap, which position always holds the lowest-valued entry?

In a heapq heap, the lowest-valued entry is always kept at position zero. [012a48290d0980da22fdb71c836b58996cafd5cf633b9acd0b56ad6afa574182]

Context grade: 2; answer grade: 2; abstention correct: N/A.

stdlib2/5 explicitly gives heap root position zero.

Citation support: [True]

Trace: `results/agent/test/hybrid_context/traces.json`, query_id `d7-t05`.

### d7-u03

Which Django command rolls back exactly the latest database migration?

The Django command to roll back the latest database migration is:

```
django-admin migrate <app_name> <migration_name>
```

To roll back to the previous migration, you would specify the migration name just before the one you want to roll back to. For example, if your latest migration is `0002_auto`, you would run:

```
django-admin migrate <app_name> 0001
```

This command effectively rolls back the latest migration by applying the previous migration. [62df0e483169e95847c412daedcccb96819fd07878433374239b27b6db5aa65e] [825e877aee1c408c8cc483cbb6288ea45efa11b6c6a51e7764101fb11b041386] [61ff6afcd5b419f70a90eb83bfd1c9bd06984a1941cc1a1b8107204a79551cbf] [8b225ef04cf56f46eecf64ce2012675472ec704ae7b3e0b685dd21b269e95c05] [69823a65c27b529f9232bb7621a82fd70a70d852586de304a182a21a299ad94c] [214dbcc9d673d510e079a85286a9af2b2e0f6090eea114cdef82574c81e31413]

Context grade: None; answer grade: N/A; abstention correct: False.

Fails abstention: invents Django rollback commands. Every citation is generic pip, exception, sys.argv or compilation text, not Django migration evidence.

Citation support: [False, False, False, False, False, False]

Trace: `results/agent/test/hybrid_context/traces.json`, query_id `d7-u03`.

### d7-u04

How does pip --require-hashes validate every dependency's archive hash?

The `pip --require-hashes` option ensures that every dependency's archive is validated against a specified hash. When you use this option, you must provide a hash for each package in your requirements file. This hash is used to verify the integrity of the downloaded package. If the hash of the downloaded package does not match the provided hash, pip will raise an error and refuse to install the package. This mechanism helps to prevent the installation of tampered or corrupted packages, ensuring that the exact version of the package you expect is the one that gets installed. [500327dd555ec10550d73e6254b930b29efd5d337bf5a069ac08970d04e9b8e1] [62df0e483169e95847c412daedcccb96819fd07878433374239b27b6db5aa65e]

Context grade: None; answer grade: N/A; abstention correct: False.

Fails abstention: describes hash-checking behavior absent from snapshot, citing pip list/freeze/install paragraphs without --require-hashes.

Citation support: [False, False]

Trace: `results/agent/test/hybrid_context/traces.json`, query_id `d7-u04`.
