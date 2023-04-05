const SECTION_PIPELINE_OPTS = "PIPELINE_OPTIONS";
const SECTION_PROCESSES = "PROCESSES";
const SECTION_PROCGROUPS = "PROCGROUPS";
const SECTION_ADDITIONAL_OPTS = "ADDITIONAL_OPTIONS";
const SECTION_RUNNING_OPTS = "RUNNING_OPTIONS";
const PROCESS_ENVS_DESC = "The options that shared by all jobs of the process";
const PROCESS_PLUGIN_OPTS_DESC = "The plugin options for the process";
const DEFAULT_DESCRIPTIONS = {
    [SECTION_PIPELINE_OPTS]: `
# Pipeline Options

These options are used to configure the pipeline, set common options and control how to run the pipeline.
`,
    [SECTION_PROCESSES]: `
# Processes

Processes are basic unit of a pipeline. Each process has its own configuration items. Some of them are derived from the pipeline options.
`,
    [SECTION_PROCGROUPS]: `
# Process Groups

Process groups are gropus of processes that run as part of the main pipeline. They are usually used to run a group of processes in a separate pipeline.
`,
    [SECTION_ADDITIONAL_OPTS]: `
# Additional Options

Additional options are used to configure the pipeline. For example, the input and output of the pipeline.
`,
    [SECTION_RUNNING_OPTS]: `
# Running Options

Running options are used to generate the command line to run the pipeline.
`
};

const JOB_TAG_KIND = {
    "0": "green",
    "-8525": "gray",
    // other: "red"
}

export {
    SECTION_PIPELINE_OPTS,
    SECTION_PROCESSES,
    SECTION_PROCGROUPS,
    SECTION_ADDITIONAL_OPTS,
    SECTION_RUNNING_OPTS,
    PROCESS_ENVS_DESC,
    PROCESS_PLUGIN_OPTS_DESC,
    DEFAULT_DESCRIPTIONS,
    JOB_TAG_KIND,
};
