<script>
// @ts-nocheck

    import { onMount } from "svelte";
    import * as itoml from "@iarna/toml";
    import TextArea from "carbon-components-svelte/src/TextArea/TextArea.svelte";
    import RadioButton from "carbon-components-svelte/src/RadioButton/RadioButton.svelte";
    import RadioButtonGroup from "carbon-components-svelte/src/RadioButtonGroup/RadioButtonGroup.svelte";
    import OptionFrame from "./OptionFrame.svelte";
    import { validateData, autoHeight, insertTab, get_pgvalue } from "../../utils";
    import { storedGlobalChanged } from "../../store";

    export let key;
    export let value;
    export let placeholder;
    export let required = false;
    export let activeNavItem;
    export let readonly = false;
    export let setError;
    export let removeError;
    export let pgargs = {};
    export let pgargkey = null;
    export let changed = false;
    export let format;

    format = format || "json";

    let invalid = false;
    let invalidText = "";
    let strValue = value;
    let origValue = value;
    let textarea = null;

    const parse = (x) => format === "json" ? JSON.parse(x) : itoml.parse(x);
    const stringify = (x) => x && (format === "json" ? JSON.stringify(x, null, 2) : itoml.stringify(x));

    if (value && typeof value === "object") {
        strValue = stringify(value);
    }

    $: pgvalue = stringify(get_pgvalue(pgargs, pgargkey === true ? key : pgargkey));
    $: if (pgvalue !== undefined && !changed) {
        strValue = pgvalue;
        value = parse(strValue);
    }

    const validateValue = (v, onmount = false) => {
        if (
            (origValue === null || origValue === undefined)
            && (v === "" || v === null || v === undefined)
            && !required
        ) {
            value = origValue;
            invalid = false;
            removeError(`${activeNavItem} / ${key}`);
            return;
        }
        const validator = required ? ["required", format] : [format];
        const error = validateData(v, validator);
        invalid = error !== null;
        invalidText = error;
        if (invalid) {
            setError(`${activeNavItem} / ${key}`, invalidText);
            // keep it
            value = v;
        } else {
            removeError(`${activeNavItem} / ${key}`);
            if (!onmount) { value = parse(v); }
        }
        autoHeight(textarea);
    };

    const useFormat = (e) => {
        if (invalid) { console.log(e); return false; }
        if (e.detail === format) { return false; }
        format = e.detail;
        strValue = stringify(value);
    };

    onMount(() => {
        if (!readonly) {
            validateValue(strValue, true);
        }
    });
</script>

<OptionFrame on:mouseenter on:mouseleave>
    <div
        slot="label"
        style='--pgarg: "This option is linked to Group Argument: {pgargkey === true ? key : pgargkey}"'
        class='{readonly ? "readonly-label" : ""} {pgargkey ? "linked-pgarg-label" : ""}'>
        {key}
        <div class="json-format-selector">
            <RadioButtonGroup disabled={invalid} selected={format} orientation="vertical" on:change={useFormat}>
                <RadioButton labelText="JSON" value="json" />
                <RadioButton labelText="TOML" value="toml" />
            </RadioButtonGroup>
        </div>
    </div>
    <div slot="field" style="align-self: flex-start;">
        <TextArea
            on:focus
            on:blur
            on:input={e => { changed = true; storedGlobalChanged.set(true); validateValue(e.target.value) }}
            on:keydown={insertTab}
            {invalid}
            {invalidText}
            {readonly}
            {placeholder}
            labelText={key}
            hideLabel
            rows={3}
            bind:value={strValue}
            bind:ref={textarea}
        />
    </div>
</OptionFrame>

<style>
    :global(.json-format-selector) {
        transform: scale(.75);
        margin-top: .2rem;
    }
</style>
