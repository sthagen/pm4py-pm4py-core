FROM python:3.12.3

RUN apt-get update
RUN apt-get -y upgrade
RUN apt-get -y install nano vim
RUN apt-get -y install git
RUN apt-get -y install python3-pydot graphviz
RUN apt-get -y install python3-tk
RUN apt-get -y install zip unzip
RUN apt-get -y install gcc gfortran libopenblas-dev liblapack-dev
RUN apt-get -y install g++ libboost-all-dev libncurses5-dev wget
RUN apt-get -y install libtool flex bison pkg-config g++ libssl-dev automake
RUN apt-get -y install libjemalloc-dev libboost-dev libboost-filesystem-dev libboost-system-dev libboost-regex-dev python3-dev autoconf flex bison cmake
RUN apt-get -y install libxml2-dev libxslt-dev libfreetype6-dev libsuitesparse-dev
RUN apt-get -y install libclang-16-dev llvm-16-dev libthrift-dev unixodbc-dev
RUN pip install -U wheel six pytest
RUN pip install -U meson-python>=0.13.1 Cython>=3.0.6 ninja spin==0.8 build setuptools_scm setuptools>=38.6.0
RUN pip install deprecation==2.1.0 graphviz==0.20.3 intervaltree==3.1.0 networkx==3.3 packaging==24.0 python-dateutil==2.9.0.post0 pytz==2024.1 six==1.16.0 sortedcontainers==2.4.0 tzdata==2024.1 
RUN pip install colorama==0.4.6 cycler==0.12.1 joblib==1.4.0 pydotplus==2.0.2 pyparsing==3.1.2 threadpoolctl==3.4.0 tqdm==4.66.2 
RUN pip install lxml==5.2.1 numpy==1.26.4 pandas==2.2.2 scipy==1.13.0 
RUN pip install contourpy==1.2.1 fonttools==4.51.0 kiwisolver==1.4.5 matplotlib==3.8.4 pillow==10.3.0 

#RUN cd / && git clone https://github.com/numpy/numpy.git && cd /numpy && git submodule update --init && pip3 install .
#RUN cd / && git clone https://github.com/pandas-dev/pandas.git && cd /pandas && pip3 install .
#RUN cd / && git clone https://github.com/scipy/scipy.git && cd /scipy && git submodule update --init && pip3 install .
#RUN cd / && git clone https://github.com/lxml/lxml.git && cd /lxml && pip3 install .
#RUN pip3 install matplotlib
#RUN cd / && git clone https://github.com/duckdb/duckdb.git && cd /duckdb && make && cd /duckdb/tools/pythonpkg && pip3 install .
#RUN cd / && git clone https://github.com/apache/arrow.git && export ARROW_HOME=/dist && export LD_LIBRARY_PATH=/dist/lib:$LD_LIBRARY_PATH && export CMAKE_PREFIX_PATH=$ARROW_HOME:$CMAKE_PREFIX_PATH && cd /arrow/ && mkdir cpp/build && cd cpp/build && cmake -DCMAKE_INSTALL_PREFIX=$ARROW_HOME -DCMAKE_INSTALL_LIBDIR=lib -DCMAKE_BUILD_TYPE=Debug -DARROW_BUILD_TESTS=ON -DARROW_COMPUTE=ON -DARROW_CSV=ON -DARROW_DATASET=ON -DARROW_FILESYSTEM=ON -DARROW_HDFS=ON -DARROW_JSON=ON -DARROW_PARQUET=ON -DARROW_WITH_BROTLI=ON -DARROW_WITH_BZ2=ON -DARROW_WITH_LZ4=ON -DARROW_WITH_SNAPPY=ON -DARROW_WITH_ZLIB=ON -DARROW_WITH_ZSTD=ON -DPARQUET_REQUIRE_ENCRYPTION=ON .. && make -j4 && make install && cd /arrow/python && export PYARROW_WITH_PARQUET=1 && export PYARROW_WITH_DATASET=1 && export PYARROW_PARALLEL=4 && python3 setup.py build_ext --inplace && python3 setup.py install
#RUN cd / && git clone https://github.com/python-greenlet/greenlet && cd /greenlet && pip3 install .
#RUN cd / && git clone https://github.com/sqlalchemy/sqlalchemy.git && cd /sqlalchemy && pip3 install .
#RUN cd / && git clone https://github.com/mkleehammer/pyodbc.git && cd /pyodbc && pip3 install .

COPY . /app
RUN cd /app && python setup.py install
