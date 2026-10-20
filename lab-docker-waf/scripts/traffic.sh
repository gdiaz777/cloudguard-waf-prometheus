#!/bin/bash
# Genera tráfico legítimo + ataques contra el WAF de forma continua (Ctrl+C para parar).
# Uso: scripts/traffic.sh [https://host-del-asset]
U=${1:-https://docker.example.com}
ATT=("rest/products/search?q=%27%20or%201%3D1--" "?q=%3Cscript%3Ealert(1)%3C/script%3E" "?file=../../../../etc/passwd" "?cmd=;cat%20/etc/passwd" "?u=*)(uid=*))(|(uid=*" "?q=%27%20UNION%20SELECT%20username,password%20FROM%20users--")
while true; do
  for i in $(seq 1 20); do curl -sk -o /dev/null $U/; curl -sk -o /dev/null "$U/rest/products/search?q=juice"; done
  curl -sk -o /dev/null -X POST -H 'Content-Type: application/json' -d '{"email":"a@a.com","password":"x"}' $U/rest/user/login
  for a in "${ATT[@]}"; do curl -sk -o /dev/null "$U/$a"; done
  curl -sk -o /dev/null -X POST -H 'Content-Type: application/json' -d "{\"email\":\"' or 1=1--\",\"password\":\"x\"}" $U/rest/user/login
  sleep 5
done
