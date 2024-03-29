<script>
    import { onMount, createEventDispatcher } from "svelte";
    import Tag from "carbon-components-svelte/src/Tag/Tag.svelte";
    import TextInput from "carbon-components-svelte/src/TextInput/TextInput.svelte";
    import Button from "carbon-components-svelte/src/Button/Button.svelte";
    import Add from "carbon-icons-svelte/lib/Add.svelte";
    import OptionFrame from "./OptionFrame.svelte";
    import { applyAtomicType, validateData, get_pgvalue } from "../../utils";
    import { storedGlobalChanged } from "../../store";

    export let key;
    export let value;
    export let activeNavItem;
    export let required;
    // item type
    export let itype;
    export let readonly = false;
    export let setError;
    export let removeError;
    export let pgargs = {};
    export let pgargkey = null;
    export let changed = false;

    let currValue = readonly ? "(readonly)" : "";
    let strValues = value || [];
    let invalid = false;
    let invalidText = "";

    let iValidator = [itype];
    let validator = required ? ["required"] : [];

    const dispatch = createEventDispatcher();

    const validateValues = (values) => {
        value = strValues.map((v) => applyAtomicType(v, itype));
        const error = validateData(values, validator);
        invalid = error !== null;
        invalidText = error;
        if (invalid) {
            setError(`${activeNavItem} / ${key}`, invalidText);
        } else {
            removeError(`${activeNavItem} / ${key}`);
        }
    };

    const validateValue = (v, validateVals=true) => {
        const error = validateData(v, iValidator);
        invalid = error !== null;
        invalidText = error;
        if (invalid) {
            setError(`${activeNavItem} / ${key}`, invalidText);
        } else {
            removeError(`${activeNavItem} / ${key}`);
            // In case there is still no values
            if (validateVals) validateValues(strValues);
        }
    };

    const addTag = () => {
        if (currValue === "") {
            return;
        }
        validateValue(currValue, false);
        if (invalid) {
            return;
        }
        strValues = [...strValues, currValue];
        currValue = "";
        validateValues(strValues);
    };

    const deleteTag = (i) => {
        strValues.splice(i, 1);
        strValues = strValues;
        validateValues(strValues);
    };

    const onBlur = (e) => {
        addTag();
        dispatch("blur", e);
    };

    const pgvalue = JSON.stringify(get_pgvalue(pgargs, pgargkey === true ? key : pgargkey));
    $: if (pgvalue !== undefined && !changed) {
        strValues = JSON.parse(pgvalue);
        value = strValues.map((v) => applyAtomicType(v, itype));
    }

    onMount(() => {
        if (!readonly) {
            validateValue(currValue);
        }
    });
</script>


<OptionFrame on:mouseenter on:mouseleave>
    <div
        slot="label"
        style='--pgarg: "This option is linked to Group Argument: {pgargkey === true ? key : pgargkey}"'
        class='{readonly ? "readonly-label" : ""} {pgargkey ? "linked-pgarg-label" : ""}'>{key}</div>
    <div slot="field">
        <div class="array-input">
            <TextInput
                size="sm"
                {invalid}
                {invalidText}
                {readonly}
                on:keyup={e => { if (e.key === "Enter" && !readonly) addTag() }}
                on:input={e => { changed = true; storedGlobalChanged.set(true); validateValue(e.detail); }}
                on:focus
                on:blur={onBlur}
                bind:value={currValue}
            />
            {#if !readonly}
            <Button size="small" kind="tertiary" iconDescription="Add item" on:click={addTag} icon={Add} />
            {/if}
        </div>
        <div class="array-tags">
            {#each strValues as strValue, i (i)}
                <Tag
                    filter={!readonly}
                    on:close={() => { deleteTag(i) } }>
                    {strValue}
                </Tag>
            {/each}
        </div>
    </div>
</OptionFrame>

<style>
    .array-input {
        display: flex;
        align-items: flex-start;
        gap: 0.2rem;
        justify-content: space-between;
        margin-right: -2.2rem;
    }
</style>