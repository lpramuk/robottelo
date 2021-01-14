# Populate token-prefix and betelgeuse depending on Satellite version.

TOKEN_PREFIX=""
POLARION_SELECTOR="name=Satellite 6"
SANITIZED_ITERATION_ID="${TEST_RUN_ID//[. ]/_}"
TEST_RUN_GROUP_ID="$(echo ${TEST_RUN_ID} | cut -d' ' -f2)"

# Prepare the XML files

betelgeuse ${TOKEN_PREFIX} test-run \
    --custom-fields "isautomated=true" \
    --custom-fields "arch=x8664" \
    --custom-fields "variant=server" \
    --custom-fields "plannedin=${SANITIZED_ITERATION_ID}" \
    --response-property "${POLARION_SELECTOR}" \
    --test-run-title "${TEST_RUN_ID}" \
    --test-run-id "${TEST_RUN_ID}" \
    --test-run-group-id "${TEST_RUN_GROUP_ID}" \
    --status inprogress \
    "./sat-${IMPORTANCE}-results.xml" \
    tests/foreman \
    "${POLARION_USERNAME}" \
    "${POLARION_PROJECT}" \
    "sat-${IMPORTANCE}-results.xml"
curl -k -u "${POLARION_USERNAME}:${POLARION_PASSWORD}" \
    -X POST -F file=@sat-${IMPORTANCE}-results.xml \
    "${POLARION_URL}import/xunit"
