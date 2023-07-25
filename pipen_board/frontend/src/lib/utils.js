import { marked } from 'marked';
import { tick } from 'svelte';
import * as itoml from "@iarna/toml";
import { SECTION_PIPELINE_OPTS, SECTION_ADDITIONAL_OPTS, SECTION_PROCESSES, SECTION_PROCGROUPS } from './constants';


function moreLikeOption(option) {
    if (!option) { return false; }
    return option.startsWith("<") || option.endsWith(">");
}

function hasHidden(data, activeNavItem) {
    return getKeysHidden(data, activeNavItem).length > 0;
}

function getKeysHidden(data, activeNavItem) {
    try {
        return Object.keys(data)
            .filter(k => data[k].hidden === true)
            .sort((a, b) => {
                if (moreLikeOption(a)) { data[a].order = data[a].order || 9999; }
                if (moreLikeOption(b)) { data[b].order = data[b].order || 9999; }
                return (data[a].order || 0) - (data[b].order || 0);
            });
    } catch (error) {
        console.error(`${activeNavItem}: ${error}`);
    }
}

function getKeysUnhidden(data, activeNavItem) {
    try {
        return Object.keys(data)
            .filter(k => data[k].hidden !== true)
            .sort((a, b) => {
                if (moreLikeOption(a)) { data[a].order = data[a].order || 9999; }
                if (moreLikeOption(b)) { data[b].order = data[b].order || 9999; }
                return (data[a].order || 0) - (data[b].order || 0);
            });
    } catch (error) {
        console.error(`${activeNavItem}: ${error}`);
    }
}

function applyAtomicType(data, type, raiseError = true) {
    try {
        if (type === "int") {
            const num = Number(data);
            if (isNaN(num) || !Number.isInteger(num)) {
                throw new Error("This field must be an integer");
            }
            return num;
        }
        if (type === "float") {
            const num = Number(data);
            if (isNaN(num) || !Number.isFinite(num)) {
                throw new Error("This field must be a number");
            }
            return num;
        }
        if (type === "auto") {
            if (["True", "TRUE", "true"].includes(data)) {
                return true;
            }
            if (["False", "FALSE", "false"].includes(data)) {
                return false;
            }
            if (["None", "NONE", "none", "null", "NULL"].includes(data)) {
                return null;
            }
            try {
                return applyAtomicType(data, "int");
            } catch (e1) {
                try {
                    return applyAtomicType(data, "float");
                } catch (e2) {
                    try {
                        return JSON.parse(data);
                    } catch (error) {
                        return data;
                    }
                }
            }
        }
    } catch (e) {
        if (raiseError) {
            throw e;
        } else {
            return data;
        }
    }
    return data
}

function validateData(data, validators) {
    for (let validator of validators) {
        if (validator === "required") {
            if (
                data === undefined
                || data === null
                || data === ""
                || (Array.isArray(data) && data.length === 0)) {
                return "This field is required";
            }
        }
        if (validator === "int") {
            data = Number(data)
            if (isNaN(data) || !Number.isInteger(data)) {
                return "This field must be an integer";
            }
        }
        if (validator === "float") {
            data = Number(data)
            if (isNaN(data) || !Number.isFinite(data)) {
                return "This field must be a number";
            }
        }
        if (validator === "json" || validator === "dict") {
            try {
                JSON.parse(data);
            } catch (e) {
                return "This field must be a valid JSON";
            }
        }
        if (validator === "toml") {
            try {
                itoml.parse(data);
            } catch (e) {
                return "This field must be a valid TOML";
            }
        }
    }
    return null;
}

function _equal(val1, val2) {
    if (val1 === val2) { return true; }
    if (val1 === undefined || val1 === null) { return false; }
    if (val2 === undefined || val2 === null) { return false; }
    if (typeof val1 !== typeof val2) { return false; }
    if (typeof val1 === "object") {
        if (Array.isArray(val1) !== Array.isArray(val2)) { return false; }
        if (Array.isArray(val1)) {
            if (val1.length !== val2.length) { return false; }
            for (let i = 0; i < val1.length; i++) {
                if (!_equal(val1[i], val2[i])) { return false; }
            }
            return true;
        }
        const keys1 = Object.keys(val1);
        const keys2 = Object.keys(val2);
        if (keys1.length !== keys2.length) { return false; }
        for (let k of keys1) {
            if (!_equal(val1[k], val2[k])) { return false; }
        }
        return true;
    }
    return false;
}

function updateConfig(config, option, value, ns=false, pgargs=null) {
    value = value || {};
    if (moreLikeOption(option)) {
        return {
            ...config,
            ...Object.fromEntries(
                value.value
                    ? value.value
                        .filter(v => v[0] !== undefined && v[0] !== null && v[0] !== "")
                        .map(v => [v[0], applyAtomicType(v[1], "auto")])
                    : []
            )
        };
    }

    if (value.type === "ns" || value.type === "namespace") { ns = true; }

    if (ns) {
        for (let popt in value.value) {
            const conf = updateConfig(config[option] || {}, popt, value.value[popt], false, pgargs);
            if (Object.keys(conf).length === 0) {
                continue;
            } else {
                config[option] = conf;
            }
        }
        return config;
    }
    if (pgargs && value.pgarg) {
        const pgvalue = get_pgvalue(pgargs, value.pgarg === true ? option : value.pgarg);
        if (pgvalue == value.value) {
            return config;
        }
    }
    if (value.value === undefined || value.value === null || _equal(value.value, value.default)) {
        return config;
    }
    return { ...config, [option]: value.value };
}

function finalizeConfig(schema) {
    let config = {};
    // Should we flatten the config (without process namespace)?
    // Only works for single-process pipelines
    const flatten = !!(
        schema[SECTION_PIPELINE_OPTS].plugin_opts
        && schema[SECTION_PIPELINE_OPTS].plugin_opts.value.args_flatten
        && schema[SECTION_PIPELINE_OPTS].plugin_opts.value.args_flatten.value
    );
    for (let [option, optinfo] of Object.entries(schema[SECTION_PIPELINE_OPTS])) {
        config = updateConfig(config, option, optinfo, option.endsWith("_opts"));
    }
    for (let [option, optinfo] of Object.entries(schema[SECTION_ADDITIONAL_OPTS] || {})) {
        config = updateConfig(config, option, optinfo);
    }
    for (let [proc, procinfo] of Object.entries(schema[SECTION_PROCESSES] || {})) {
        let proc_conf = {};
        for (let [option, optinfo] of Object.entries(procinfo.value || {})) {
            proc_conf = updateConfig(
                proc_conf,
                option,
                optinfo,
                option.endsWith("_opts") || option === "envs"
            );
            // remove options that are equal to the pipeline options
            if (_equal(proc_conf[option], config[option])) { delete proc_conf[option]; }
        }
        if (Object.keys(proc_conf).length > 0) {
            if (flatten) {
                config = { ...config, ...proc_conf };
            } else {
                config[proc] = proc_conf;
            }
        }
    }
    for (let [group, groupinfo] of Object.entries(schema[SECTION_PROCGROUPS] || {})) {
        for (let option in groupinfo.ARGUMENTS) {
            const conf = updateConfig(config[group] || {}, option, groupinfo.ARGUMENTS[option]);
            if (Object.keys(conf).length > 0) {
                config[group] = conf;
            }
        }
        for (let [proc, procinfo] of Object.entries(groupinfo.PROCESSES)) {
            let proc_conf = {};
            for (let [option, optinfo] of Object.entries(procinfo.value || {})) {
                proc_conf = updateConfig(
                    proc_conf,
                    option,
                    optinfo,
                    option.endsWith("_opts") || option === "envs",
                    groupinfo.ARGUMENTS
                );
                // remove options that are equal to the pipeline options
                if (_equal(proc_conf[option], config[option])) { delete proc_conf[option]; }
            }
            if (Object.keys(proc_conf).length > 0) config[proc] = proc_conf;
        }
    }

    return config;
}

function _formatTextWithCodeBlocks(input) {
    // wrap multiple-line code starting with >>>
    // like this:
    // >>> code
    // >>> more code
    // to:
    // ```
    // code
    // more code
    // ```
    const lines = input.split('\n');
    let formattedString = '';
    let isCodeBlock = false;

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];

        if (line.startsWith('>>> ')) {
        if (!isCodeBlock) {
            formattedString += '```\n';
            isCodeBlock = true;
        }
        formattedString += line.slice(4) + '\n';
        } else {
        if (isCodeBlock) {
            formattedString += '```\n';
            isCodeBlock = false;
        }
        formattedString += line + '\n';
        }
    }

    if (isCodeBlock) {
        formattedString += '```\n';
    }

    return formattedString;
}

function _formatSentencesIntoParagraphs(input) {
    // make sentences in <p> tags into multiple <p> tags
    // the sentences should end with . and followed by a newline
    // like this:
    // <p>first sentence.\nsecond sentence.</p>
    // to:
    // <p>first sentence.</p>
    // <p>second sentence.</p>
    const regex = /<p>([\s\S]*?)<\/p>/gi;
    return input.replace(regex, (m, p) => {
        return '<p>' + p.replace(/\.\n/g, '.</p>\n<p>') + '</p>';
    });
}

function parseMarkdown(text) {
    if (text === undefined || text === null) { return ''; }
    const hooks = {
        preprocess(markdown) {
            return _formatTextWithCodeBlocks(markdown);
        },
        postprocess(html) {
            return _formatSentencesIntoParagraphs(html);
        },
    };
    // https://github.com/markedjs/marked/issues/2793
    // @ts-ignore
    marked.use({ hooks, silent: true });

    const renderer = new marked.Renderer();
    const linkRenderer = renderer.link;
    renderer.link = (href, title, text) => {
        const html = linkRenderer.call(renderer, href, title, text);
        return html.replace(/^<a /, '<a target="_blank" title="Open in New Window" rel="noopener" ');
    };
    return marked.parse(text, { renderer });
}

function autoHeight(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = `calc(${textarea.scrollHeight}px + .2rem)`;
}

const insertTab = async function(e) {
    if (e.key === "Tab") {
        e.preventDefault();
        const { selectionStart, selectionEnd, value } = this;
        const before = value.substring(0, selectionStart);
        const after = value.substring(selectionEnd);
        this.value = before + "\t" + after;
        await tick();
        this.selectionStart = this.selectionEnd = selectionStart + 1;
    }
}

const getStatusPercentage = function(data) {
    let counts = {succeeded: 0, failed: 0, running: 0, init: 0};

    for (let proc in data[SECTION_PROCESSES]) {
        counts[data[SECTION_PROCESSES][proc].status] += 1;
    }

    for (let group in data[SECTION_PROCGROUPS]) {
        for (let proc in data[SECTION_PROCGROUPS][group]) {
            counts[data[SECTION_PROCGROUPS][group][proc].status] += 1;
        }
    }
    const total = counts.succeeded + counts.failed + counts.running + counts.init;
    if (total === 0) {
        return [0, 0, 0, 100];
    }
    return [
        (counts.succeeded / total) * 100,
        (counts.failed / total) * 100,
        (counts.running / total) * 100,
        (counts.init / total) * 100,
    ];
};


const fetchAPI = async function(url, options, result = "json") {
    let response;
    try {
        response = await fetch(url, options);
    } catch (e) {
        throw new Error(`Failed to fetch ${url}: ${e}`);
    }
    if (!response.ok) {
        throw new Error(`Failed to fetch ${url}: ${response.status} ${response.statusText}`);
    }
    if (result === "json") {
        return await response.json();
    } else if (result === "text") {
        return await response.text();
    } else if (result === "blob") {
        return await response.blob();
    } else {
        return response;
    }
};

function get_pgvalue(pgargs, pgargkey) {
    // get the value of a process group argument
    if (pgargs === undefined || pgargs === null) { return undefined; }
    if (Object.keys(pgargs).length === 0) { return undefined; }
    if (pgargkey === undefined || pgargkey === null) { return undefined; }
    if (pgargkey === '') { return undefined; }
    if (!pgargkey.includes('.')) { return pgargs[pgargkey] && pgargs[pgargkey].value; }
    const keys = pgargkey.split('.');
    let value = pgargs;
    for (let key of keys) {
        if (value === undefined || value === null) { return undefined; }
        value = value[key] && value[key].value;
    }
    return value;
}

const IS_DEV = window.location.search.includes('dev=1');


export {
    validateData,
    moreLikeOption,
    finalizeConfig,
    hasHidden,
    getKeysHidden,
    getKeysUnhidden,
    applyAtomicType,
    parseMarkdown,
    autoHeight,
    insertTab,
    getStatusPercentage,
    fetchAPI,
    get_pgvalue,
    IS_DEV,
};
