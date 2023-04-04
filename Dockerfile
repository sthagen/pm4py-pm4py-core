FROM python:3.11

RUN apt-get update
RUN apt-get -y upgrade
RUN apt-get -y install nano vim
RUN apt-get -y install git
RUN apt-get -y install python3-pydot graphviz
RUN apt-get -y install python3-tk
RUN apt-get -y install zip unzip
RUN apt-get -y install gcc gfortran python-dev libopenblas-dev liblapack-dev
RUN apt-get -y install g++ libboost-all-dev libncurses5-dev wget
RUN apt-get -y install libtool flex bison pkg-config g++ libssl-dev automake
RUN apt-get -y install libjemalloc-dev libboost-dev libboost-filesystem-dev libboost-system-dev libboost-regex-dev python3-dev autoconf flex bison cmake
RUN apt-get -y install libxml2-dev libxslt-dev libfreetype6-dev libsuitesparse-dev
RUN pip install -U wheel six pytest
RUN pip install colorama==0.4.6 contourpy==1.0.7 cycler==0.11.0 deprecation==2.1.0 fonttools==4.39.3 graphviz==0.20.1 intervaltree==3.1.0 kiwisolver==1.4.4 lxml==4.9.2 matplotlib==3.7.1 networkx==3.0 numpy==1.24.2 packaging==23.0 pandas==1.5.3 pillow==9.5.0 pydotplus==2.0.2 pyparsing==3.0.9 python-dateutil==2.8.2 pytz==2023.3 scipy==1.10.1 six==1.16.0 sortedcontainers==2.4.0 stringdist==1.0.9 tqdm==4.65.0 

COPY . /app
RUN cd /app && python setup.py install
