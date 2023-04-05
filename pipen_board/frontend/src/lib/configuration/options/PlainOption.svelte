<script>
    import { onMount } from "svelte";
    import TextInput from "carbon-components-svelte/src/TextInput/TextInput.svelte";
    import { applyAtomicType, validateData } from "../../utils.js";
    import { setError, removeError } from "../../store.js";

    export let key;
    export let value;
    export let placeholder;
    export let optionType = "str";
    export let required = false;
    export let activeNavItem;
    export let storeError = true;
    export let readonly = false;

    let setErrorFun;
    let removeErrorFun;
    if (!storeError) {
        setErrorFun = (key, value) => {};
        removeErrorFun = (key) => {};
    } else {
        setErrorFun = setError;
        removeErrorFun = removeError;
    }

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
        ) {
            value = origValue;
            return;
        }
        const error = validateData(v, validator);
        invalid = error !== null;
        invalidText = error;
        if (invalid) {
            setErrorFun(`${activeNavItem} / ${key}`, invalidText);
        } else {
            removeErrorFun(`${activeNavItem} / ${key}`);
        }
    };

    $: if (!(strValue === "" && (origValue === null || origValue === undefined))) {
        value = applyAtomicType(strValue, optionType, false);
    }

    onMount(() => {
        if (!readonly) {
            validateValue(strValue);
        }
    });
</script>

<TextInput
    on:mouseenter
    on:mouseleave
    on:focus
    on:blur
    on:input={e => validateValue(e.detail)}
    {invalid}
    {invalidText}
    {readonly}
    inline
    size="sm"
    placeholder={placeholder}
    labelText={readonly ? `${key} (readonly)` : key}
    bind:value={strValue}
/>
