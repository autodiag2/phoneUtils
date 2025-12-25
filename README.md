# phoneUtils
Utils for phones

### Develop
#### Install
```bash
conda create -y -n phoneutils python=3.11 ; \
    conda activate phoneutils && \
    pip install poetry && \
    poetry install --no-root && \
    pip install -e .
```
#### Build
```bash
poetry build
```