"""Runs the state snap again, verbosely, on the world as it stands."""
import world2 as W
import palsnap
import world2 as W

print(palsnap.snap_states(verbose=True)[-5:])
