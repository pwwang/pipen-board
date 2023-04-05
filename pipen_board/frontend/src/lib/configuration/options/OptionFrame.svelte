<div style="display: flex;" on:mouseenter on:mouseleave>
    <div class="bx--form-item bx--text-input-wrapper bx--text-input-wrapper--inline">
        <div class="bx--text-input__label-helper-wrapper">
        <label
            class="bx--label bx--label--inline bx--label--inline--sm">
            <slot name="label" />
        </label>
    </div>
        <slot name="field" />
    </div>
</div>
