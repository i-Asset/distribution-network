FROM grafana/grafana:6.2.5

USER root

RUN apt-get update && \
  apt-get install -y --no-install-recommends \
  gettext

# in the container you just started:
RUN chown -R root:root /etc/grafana && \
  chmod -R a+r /etc/grafana && \
  chown -R grafana:grafana /var/lib/grafana && \
  chown -R grafana:grafana /usr/share/grafana

RUN grafana-cli plugins install grafana-worldmap-panel

# the files Dashboard-system.json, dashboard.yml and source.yml are generic and adaptable using the .env-file
RUN mkdir -p /var/lib/grafana/dashboards
ADD ./Dashboard-system.json /var/lib/grafana/dashboards
ADD ./provisioning/dashboards/dashboard.yml /etc/grafana/provisioning/dashboards
ADD ./provisioning/datasources/source.yml /etc/grafana/provisioning/datasources

ENTRYPOINT envsubst < /etc/grafana/provisioning/datasources/source.yml > tmp.yml && mv tmp.yml /etc/grafana/provisioning/datasources/source.yml \
  && envsubst < /var/lib/grafana/dashboards/Dashboard-system.json > tmp.json && mv tmp.json /var/lib/grafana/dashboards/Dashboard-system.json \
  && su grafana && sh /run.sh
