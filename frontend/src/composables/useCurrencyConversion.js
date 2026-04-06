import { watch } from "vue"

export function useCurrencyConversion(formFields, doc, fieldsToConvert = []) {
	const currencyFields = new Set([...fieldsToConvert])

	const updateLabels = () => {
		formFields.data?.forEach((field) => {
			if (!field?.fieldname) return
			if (!currencyFields.has(field.fieldname)) return

			if (!field._original_label && field.label) {
				field._original_label = field.label.replace(/\([^\)]*\)/g, "").trim()
			}
			if (currencyFields.has(field.fieldname)) {
				field.label = `${field._original_label} (${doc.value.currency})`
			}
		})
	}

	watch(
		() => doc.value?.currency,
		() => {
			updateLabels()
		},
		{ immediate: true }
	)

	watch(
		() => formFields.data,
		() => {
			updateLabels()
		},
		{ deep: true, immediate: true }
	)

	return { updateLabels }
}