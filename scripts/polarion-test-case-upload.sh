# requires betelgeuse pypi package

betelgeuse requirement tests/foreman/ "${POLARION_PROJECT}" "requirement.xml"
curl -k -u "${POLARION_USERNAME}:${POLARION_PASSWORD}" \
    -X POST -F file=@requirement.xml \
    "${POLARION_URL}import/requirement"

export PYTHONPATH="${PWD}"

cat > betelgeuse_config.py <<EOF
from betelgeuse import default_config
DEFAULT_APPROVERS_VALUE = '${POLARION_USERNAME}:approved'
DEFAULT_STATUS_VALUE = 'approved'
DEFAULT_SUBTYPE2_VALUE = '-'
TESTCASE_CUSTOM_FIELDS = default_config.TESTCASE_CUSTOM_FIELDS + ('customerscenario',)
TRANSFORM_CUSTOMERSCENARIO_VALUE = default_config._transform_to_lower
DEFAULT_CUSTOMERSCENARIO_VALUE = 'false'
EOF

betelgeuse --config-module "betelgeuse_config" test-case \
    --response-property "satellite6=testcases" \
    --automation-script-format "https://github.com/SatelliteQE/robottelo/blob/master/{path}#L{line_number}" \
    tests/foreman/ "${POLARION_PROJECT}" polarion-test-cases.xml
curl -k -u "${POLARION_USERNAME}:${POLARION_PASSWORD}" \
    -X POST -F file=@polarion-test-cases.xml \
    "${POLARION_URL}import/testcase"
