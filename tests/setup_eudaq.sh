git clone -b v1.x-dev https://github.com/eudaq/eudaq  # FIXME: silab repo for now
cd eudaq/build
cmake -DBUILD_python=ON -DBUILD_gui=OFF -DBUILD_onlinemon=OFF -DBUILD_runsplitter=OFF -DUSE_ROOT=OFF ..
make install -j 4
cd ${PWD}/../python/
export PYTHONPATH="${PYTHONPATH}:${PWD}"
cd ../..