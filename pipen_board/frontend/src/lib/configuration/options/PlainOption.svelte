<script>
    import { onMount } from "svelte";
    import TextInput from "carbon-components-svelte/src/TextInput/TextInput.svelte";
    import { applyAtomicType, validateData, get_pgvalue } from "../../utils.js";
    import { storedGlobalChanged } from "../../store.js";

    export let key;
    export let value;
    export let placeholder;
    export let optionType = "str";
    export let required = false;
    export let activeNavItem;
    export let readonly = false;
    export let defValue;
    export let setError;
    export let removeError;
    export let pgargs = {};
    export let pgargkey = null;
    export let changed = false;

    let invalid = false;
    let invalidText = "";
    let strValue = value;
    let origValue = value;
    let validator = [optionType];
    if (required) {
        validator = ["required", ...validator];
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
            if (v === "") { value = defValue; }
            removeError(`${activeNavItem} / ${key}`);
        }
    };

    $: if (!(strValue === "" && (origValue === null || origValue === undefined))) {
        value = applyAtomicType(strValue, optionType, false);
    }

    $: pgvalue = get_pgvalue(pgargs, pgargkey === true ? key : pgargkey);
    $: if (pgvalue !== undefined && !changed) {
        strValue = pgvalue;
    }

    onMount(() => {
        if (!readonly) {
            validateValue(strValue);
        }
    });
</script>

<div
    class="textinput-wrapper {pgargkey ? 'linked-pgarg' : ''}"
    style='--pgarg: "This option is linked to Group Argument: {pgargkey === true ? key : pgargkey}"'>
    <TextInput
        on:mouseenter
        on:mouseleave
        on:focus
        on:blur
        on:input={e => {changed = true; storedGlobalChanged.set(true); validateValue(e.detail)}}
        {invalid}
        {invalidText}
        {readonly}
        inline
        size="sm"
        class={readonly ? "readonly" : ""}
        placeholder={placeholder}
        labelText={key}
        bind:value={strValue}
    />
</div>
