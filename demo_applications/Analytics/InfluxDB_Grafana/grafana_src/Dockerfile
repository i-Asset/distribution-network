FROM grafana/grafana:8.1.1-ubuntu

USER root

RUN apt-get update && \
  apt-get install -y --no-install-recommends \
  gettext

# in the container you just started:
RUN chown -R root:root /etc/grafana && \
  chmod -R a+r /etc/grafana && \
  chown -R grafana:472 /var/lib/grafana && \
  chown -R grafana:472 /usr/share/grafana

RUN grafana-cli plugins install grafana-worldmap-panel

# the files Dashboard-system.json, dashboard.yml and source.yml are generic and adaptable using the .env-file
RUN mkdir -p /var/lib/grafana/dashboards
ADD ./Dashboard-system.json /var/lib/grafana/dashboards
ADD ./provisioning/dashboards/dashboard.yml /etc/grafana/provisioning/dashboards
ADD ./provisioning/datasources/source.yml /etc/grafana/provisioning/datasources

# change permission for the added files
RUN chown -R grafana:472 /var/lib/grafana/dashboards && \
  chown -R grafana:472 /etc/grafana/provisioning

ENTRYPOINT envsubst < /etc/grafana/provisioning/datasources/source.yml > tmp.yml && mv tmp.yml /etc/grafana/provisioning/datasources/source.yml \
  && envsubst < /var/lib/grafana/dashboards/Dashboard-system.json > tmp.json && mv tmp.json /var/lib/grafana/dashboards/Dashboard-system.json \
  && sh /run.sh
