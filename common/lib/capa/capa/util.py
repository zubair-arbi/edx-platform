from calc import evaluator
from cmath import isinf

#-----------------------------------------------------------------------------
#
# Utility functions used in CAPA responsetypes
default_tolerance = '0.001%'


def compare_with_tolerance(complex1, complex2, tolerance=default_tolerance, relative_tolerance=False):
    """
    Compare complex1 to complex2 with maximum tolerance tol.

    If tolerance is type string, then it is counted as relative if it ends in %; otherwise, it is absolute.

     - complex1    :  student result (float complex number)
     - complex2    :  instructor result (float complex number)
     - tolerance   :  string representing a number or float
     - relative_tolerance: bool, used when`tolerance` is float to explicitly use passed tolerance as relative.

     Default tolerance of 1e-3% is added to compare two floats for
     near-equality (to handle machine representation errors).
     Default tolerance is relative, as the acceptable difference between two
     floats depends on the magnitude of the floats.
     (http://randomascii.wordpress.com/2012/02/25/comparing-floating-point-numbers-2012-edition/)
     Examples:
        In [183]: 0.000016 - 1.6*10**-5
        Out[183]: -3.3881317890172014e-21
        In [212]: 1.9e24 - 1.9*10**24
        Out[212]: 268435456.0
    """
    if relative_tolerance:
        tolerance = tolerance * max(abs(complex1), abs(complex2))
    elif tolerance.endswith('%'):
        tolerance = evaluator(dict(), dict(), tolerance[:-1]) * 0.01
        tolerance = tolerance * max(abs(complex1), abs(complex2))
    else:
        tolerance = evaluator(dict(), dict(), tolerance)

    if isinf(complex1) or isinf(complex2):
        # If an input is infinite, we can end up with `abs(complex1-complex2)` and
        # `tolerance` both equal to infinity. Then, below we would have
        # `inf <= inf` which is a fail. Instead, compare directly.
        return complex1 == complex2
    else:
        # v1 and v2 are, in general, complex numbers:
        # there are some notes about backward compatibility issue: see responsetypes.get_staff_ans()).
        return abs(complex1 - complex2) <= tolerance


def contextualize_text(text, context):  # private
    """
    Takes a string with variables. E.g. $a+$b.
    Does a substitution of those variables from the context
    """
    if not text:
        return text
    for key in sorted(context, lambda x, y: cmp(len(y), len(x))):
        # TODO (vshnayder): This whole replacement thing is a big hack
        # right now--context contains not just the vars defined in the
        # program, but also e.g. a reference to the numpy module.
        # Should be a separate dict of variables that should be
        # replaced.
        if '$' + key in text:
            try:
                s = str(context[key])
            except UnicodeEncodeError:
                s = context[key].encode('utf8', errors='ignore')
            text = text.replace('$' + key, s)
    return text


def convert_files_to_filenames(answers):
    """
    Check for File objects in the dict of submitted answers,
        convert File objects to their filename (string)
    """
    new_answers = dict()
    for answer_id in answers.keys():
        answer = answers[answer_id]
        # Files are stored as a list, even if one file
        if is_list_of_files(answer):
            new_answers[answer_id] = [f.name for f in answer]
        else:
            new_answers[answer_id] = answers[answer_id]
    return new_answers


def is_list_of_files(files):
    return isinstance(files, list) and all(is_file(f) for f in files)


def is_file(file_to_test):
    """
    Duck typing to check if 'file_to_test' is a File object
    """
    return all(hasattr(file_to_test, method) for method in ['read', 'name'])


def find_with_default(node, path, default):
    """
    Look for a child of node using , and return its text if found.
    Otherwise returns default.

    Arguments:
       node: lxml node
       path: xpath search expression
       default: value to return if nothing found

    Returns:
       node.find(path).text if the find succeeds, default otherwise.

    """
    v = node.find(path)
    if v is not None:
        return v.text
    else:
        return default
