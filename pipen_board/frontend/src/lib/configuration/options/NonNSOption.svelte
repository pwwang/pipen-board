<script>
    import { moreLikeOption } from "../../utils.js";
    import PlainOption from "./PlainOption.svelte";
    import BoolOption from "./BoolOption.svelte";
    import TextOption from "./TextOption.svelte";
    import ChoiceOption from "./ChoiceOption.svelte";
    import MChoicesOption from "./MChoicesOption.svelte";
    import ArrayOption from "./ArrayOption.svelte";
    import AutoOption from "./AutoOption.svelte";
    import MoreLikeOption from "./MoreLikeOption.svelte";
    import JsonOption from "./JsonOption.svelte";
    import { descFocused } from "../../store.js";

    export let key;
    export let data;
    export let activeNavItem;
    export let description;
    export let readonly = false;
    export let setError;
    export let removeError;

    const focusTail = "                    "
    let oldDescription = description || "";

    const onMouseEnter = () => {
        if (!description || !description.endsWith(focusTail)) {
            description = data.desc;
        }
    };

    const onMouseLeave = () => {
        if (!description || !description.endsWith(focusTail)) {
            description = oldDescription;
        }
    };

    const onFocus = () => {
        description = data.desc + focusTail;
        descFocused.set(false);
    };

    const onBlur = () => {
        if (!$descFocused) {
            description = oldDescription;
        } else if (description.endsWith(focusTail)) {
            description = description.substring(0, description.length - focusTail.length);
        }
    };

</script>

{#if moreLikeOption(key)}
<MoreLikeOption
    on:mouseenter={onMouseEnter}
    on:mouseleave={onMouseLeave}
    on:focus={onFocus}
    on:blur={onBlur}
    {key}
    bind:value={data.value}
    />
{:else if data.type === 'bool'}
<BoolOption
    on:mouseenter={onMouseEnter}
    on:mouseleave={onMouseLeave}
    on:focus={onFocus}
    on:blur={onBlur}
    {key}
    readonly={readonly || data.readonly}
    bind:value={data.value}
    />
{:else if data.type === 'text'}
<TextOption
    on:mouseenter={onMouseEnter}
    on:mouseleave={onMouseLeave}
    on:focus={onFocus}
    on:blur={onBlur}
    required={data.required}
    placeholder={data.placeholder}
    readonly={readonly || data.readonly}
    {activeNavItem}
    {setError}
    {removeError}
    {key}
    bind:value={data.value}
    />
{:else if data.type === 'choice'}
<ChoiceOption
    on:mouseenter={onMouseEnter}
    on:mouseleave={onMouseLeave}
    on:focus={onFocus}
    on:blur={onBlur}
    {key}
    required={data.required}
    readonly={readonly || data.readonly}
    choices={data.choices}
    choicesDesc={data.choices_desc}
    bind:value={data.value}
    />
{:else if data.type === 'mchoices' || data.type === 'mchoice'}
<MChoicesOption
    on:blur={onBlur}
    on:focus={onFocus}
    on:mouseenter={onMouseEnter}
    on:mouseleave={onMouseLeave}
    {key}
    {activeNavItem}
    {setError}
    {removeError}
    required={data.required}
    readonly={readonly || data.readonly}
    choices={data.choices}
    choicesDesc={data.choices_desc}
    bind:value={data.value}
    />
{:else if data.type === 'json'}
<JsonOption
    on:mouseenter={onMouseEnter}
    on:mouseleave={onMouseLeave}
    on:focus={onFocus}
    on:blur={onBlur}
    required={data.required}
    placeholder={data.placeholder}
    readonly={readonly || data.readonly}
    {key}
    {activeNavItem}
    {setError}
    {removeError}
    bind:value={data.value}
    />
{:else if data.type === 'auto'}
<AutoOption
    on:mouseenter={onMouseEnter}
    on:mouseleave={onMouseLeave}
    on:focus={onFocus}
    on:blur={onBlur}
    required={data.required}
    readonly={readonly || data.readonly}
    placeholder={data.placeholder}
    {key}
    {activeNavItem}
    {setError}
    {removeError}
    bind:value={data.value}
    />
{:else if data.type === 'list' || data.type === 'array'}
<ArrayOption
    on:mouseenter={onMouseEnter}
    on:mouseleave={onMouseLeave}
    on:focus={onFocus}
    on:blur={onBlur}
    required={data.required}
    readonly={readonly || data.readonly}
    itype={data.itype}
    {key}
    {activeNavItem}
    {setError}
    {removeError}
    bind:value={data.value}
    />
{:else}
<PlainOption
    on:mouseenter={onMouseEnter}
    on:mouseleave={onMouseLeave}
    on:focus={onFocus}
    on:blur={onBlur}
    optionType={data.type}
    required={data.required}
    readonly={readonly || data.readonly}
    {activeNavItem}
    {key}
    {setError}
    {removeError}
    placeholder={data.placeholder}
    bind:value={data.value}
    />
{/if}
