<script>
// @ts-nocheck

    import { onMount } from "svelte";
    import TextArea from "carbon-components-svelte/src/TextArea/TextArea.svelte";
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

    let validator = [];
    let invalid = false;
    let invalidText = "";
    let origValue = value;
    let textarea = null;

    if (required) {
        validator = ["required", ...validator]
    }

    const validateValue = (v) => {
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
        const error = validateData(v, validator);
        invalid = error !== null;
        invalidText = error;
        if (invalid) {
            setError(`${activeNavItem} / ${key}`, invalidText);
        } else {
            removeError(`${activeNavItem} / ${key}`);
        }
        autoHeight(textarea);
    };

    $: pgvalue = get_pgvalue(pgargs, pgargkey === true ? key : pgargkey);
    $: if (pgvalue !== undefined && !changed) {
        value = pgvalue;
    }

    onMount(() => {
        if (!readonly) {
            validateValue(value);
        }
    });
</script>

<OptionFrame on:mouseenter on:mouseleave>
    <div
        slot="label"
        style='--pgarg: "This option is linked to Group Argument: {pgargkey === true ? key : pgargkey}"'
        class='{readonly ? "readonly-label" : ""} {pgargkey ? "linked-pgarg-label" : ""}'>{key}</div>
    <div slot="field">
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
            rows={1}
            bind:ref={textarea}
            bind:value={value}
        />
    </div>
</OptionFrame>
