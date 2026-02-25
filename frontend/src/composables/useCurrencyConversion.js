import { ref, watch } from "vue"
import { getCompanyCurrency, currencyPrecision } from "@/data/currencies"

const flt = (value, precision) => {
	const num = parseFloat(value) || 0;
	const targetPrecision = precision !== undefined ? precision : (currencyPrecision.data || 2);
	return parseFloat(num.toFixed(targetPrecision));
};

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

	// update labels
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

// function to update base currency fields data
export function updateBaseFieldsAmount({doc, fields, exchangeRate}) {
	if (!doc) return;
	const excahnge_rate = flt(exchangeRate || doc.exchange_rate || 1, 9);
	fields.forEach(f => {
		const val = flt(flt(doc[f]) * excahnge_rate);
		doc["base_" + f] = val;
	});
}