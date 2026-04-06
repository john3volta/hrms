import { watch } from "vue"

export function updateCurrencyLabels({ formFields, doc, transactionFields = []}) {
	if (!formFields || !doc) return
	const currencyFields = new Set([...transactionFields])

	const updateLabels = () => {
		formFields.forEach((field) => {
			if (!field?.fieldname) return
			if (!currencyFields.has(field.fieldname)) return

			if (!field._original_label && field.label) {
				field._original_label = field.label.replace(/\([^\)]*\)/g, "").trim()
			}
			if (transactionFields.includes(field.fieldname)) {
				field.label = `${field._original_label} (${doc.currency})`
			}
		})
	}

	// update labels
	watch(
		() => doc.currency,
		updateLabels,
		{ immediate: true }
	)

	return { updateLabels}
}