FROM apache/airflow:2.8.1-python3.11

USER root
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
         build-essential \
         libgtk2.0-dev \
         libgdal-dev \
         unixodbc-dev \
         libpq-dev \
         vim \
         unzip \
         git \
         curl \
  && sed -i 's,^\(MinProtocol[ ]*=\).*,\1'TLSv1.0',g' /etc/ssl/openssl.cnf \
  && sed -i 's,^\(CipherString[ ]*=\).*,\1'DEFAULT@SECLEVEL=1',g' /etc/ssl/openssl.cnf \
  && curl -O http://acraiz.icpbrasil.gov.br/credenciadas/CertificadosAC-ICP-Brasil/ACcompactado.zip \
  && unzip -o ACcompactado.zip -d /usr/local/share/ca-certificates/ \
  && update-ca-certificates \
  && apt-get autoremove -yqq --purge \
  && apt-get clean \
  && rm -rf \
    /var/lib/apt/lists/* \
    /tmp/* \
    /var/tmp/* \
    /usr/share/man \
    /usr/share/doc \
    /usr/share/doc-base \
  && sed -i 's/^# en_US.UTF-8 UTF-8$/en_US.UTF-8 UTF-8/g' /etc/locale.gen \
  && sed -i 's/^# pt_BR.UTF-8 UTF-8$/pt_BR.UTF-8 UTF-8/g' /etc/locale.gen \
  && locale-gen en_US.UTF-8 pt_BR.UTF-8 \
  && update-locale LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8

USER airflow
WORKDIR ${AIRFLOW_HOME}

# Para rodar o airflow só precisamos instalar as dependências visto que o código
# sempre será sincronizado via git sync ou via volumes localmente
COPY requirements.txt .
RUN pip install -r requirements.txt

# ==============================================================================
# CONFIGURAÇÃO DO DBT CENTRAL (POC MULTI-TENANT)
# ==============================================================================

# 1. Garante a criação da estrutura de pastas do DBT no container
RUN mkdir -p dags/dbt

# 2. Copia os arquivos de configuração do DBT para dentro do container
# Certifique-se de que esses arquivos existem na sua máquina local neste mesmo caminho
COPY airflow_lappis/dags/dbt/dbt_project.yml dags/dbt/
COPY airflow_lappis/dags/dbt/packages.yml dags/dbt/

# 3. Entra na pasta do DBT e baixa os pacotes dos clientes (IPEA e MIR) do GitHub
WORKDIR ${AIRFLOW_HOME}/dags/dbt
RUN dbt deps

# 4. Retorna o WORKDIR para a raiz do Airflow para manter o padrão da imagem
WORKDIR ${AIRFLOW_HOME}