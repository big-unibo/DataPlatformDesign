#!/bin/bash
for dir in */     # list directories in the form "/tmp/dirname/"
do
    dir=${dir%*/}
    echo "$dir"    # print everything after the final "/"
    rm ./$dir/output/* || true
done
