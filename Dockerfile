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
RUN apt-get -y install libclang-16-dev llvm-16-dev
RUN pip install -U wheel six pytest
RUN pip install -U meson-python>=0.13.1 Cython>=3.0.6 ninja spin==0.8 build
RUN pip install deprecation==2.1.0 graphviz==0.20.3 intervaltree==3.1.0 networkx==3.3 packaging==24.0 python-dateutil==2.9.0.post0 pytz==2024.1 six==1.16.0 sortedcontainers==2.4.0 tzdata==2024.1 
RUN pip install colorama==0.4.6 cycler==0.12.1 joblib==1.4.0 pydotplus==2.0.2 pyparsing==3.1.2 threadpoolctl==3.4.0 tqdm==4.66.2 
RUN pip install lxml==5.2.1 numpy==1.26.4 pandas==2.2.2 scipy==1.13.0 
RUN pip install contourpy==1.2.1 fonttools==4.51.0 kiwisolver==1.4.5 matplotlib==3.8.4 pillow==10.3.0 

#RUN cd / && git clone https://github.com/numpy/numpy.git && cd /numpy && git submodule update --init && pip3 install .
#RUN cd / && git clone https://github.com/pandas-dev/pandas.git && cd /pandas && pip3 install .
#RUN cd / && git clone https://github.com/scipy/scipy.git && cd /scipy && git submodule update --init && pip3 install .
#RUN cd / && git clone https://github.com/lxml/lxml.git && cd /lxml && pip3 install .
#RUN pip3 install matplotlib
#RUN cd / && git clone https://github.com/duckdb/duckdb.git && cd /duckdb && make && cd /duckdb/tools/pythonpkg && python3 setup.py install

COPY . /app
RUN cd /app && python setup.py install
