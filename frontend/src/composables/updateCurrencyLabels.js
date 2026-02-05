import { ref, watch } from "vue"
import { getCompanyCurrency } from "@/data/currencies"

export function updateCurrencyLabels({ formFields, doc, baseFields = [], transactionFields = []}) {	
	if (!formFields || !doc) return

	const companyCurrency = ref("")

	// fetch company currency initially or when company changes
	const fetchCompanyCurrency = async () => {
		if (!doc.company) return
		companyCurrency.value = await getCompanyCurrency(doc.company)
	}

	const currencyFields = new Set([...baseFields, ...transactionFields])

	const updateLabels = () => {
		if (!companyCurrency.value) return

		formFields.forEach((field) => {
			if (!field?.fieldname) return
			if (!currencyFields.has(field.fieldname)) return

			if (!field._original_label && field.label) {
				field._original_label = field.label.replace(/\([^\)]*\)/g, "").trim()
			}

			if (baseFields.includes(field.fieldname)) {
				field.label = `${field._original_label} (${companyCurrency.value})`
				field.hidden = doc.currency === companyCurrency.value
			}

			if (transactionFields.includes(field.fieldname)) {
				field.label = `${field._original_label} (${doc.currency})`
			}
		})
	}

	// update labels script
	watch(
		() => [doc.company, doc.currency],
		async () => {
			await fetchCompanyCurrency()
			updateLabels()
		},
		{ immediate: true }
	)

	return { updateLabels, companyCurrency }
}
