<template>
	<ion-page>
		<ion-content :fullscreen="true">
			<FormView
				v-if="formFields.data"
				doctype="Employee Advance"
				v-model="employeeAdvance"
				:isSubmittable="true"
				:fields="formFields.data"
				:id="props.id"
				:showAttachmentView="true"
				@validateForm="validateForm"
			/>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { IonPage, IonContent } from "@ionic/vue"
import { createResource } from "frappe-ui"
import { ref, watch, inject } from "vue"

import FormView from "@/components/FormView.vue"
import { updateCurrencyLabels } from "@/composables/useCurrencyConversion"

const employee = inject("$employee")

const props = defineProps({
	id: {
		type: String,
		required: false,
	},
})

// object to store form data
const employeeAdvance = ref({
	employee: employee.data.name,
	employee_name: employee.data.employee_name,
	company: employee.data.company,
	department: employee.data.department,
})

// get form fields
const formFields = createResource({
	url: "hrms.api.get_doctype_fields",
	params: { doctype: "Employee Advance" },
	transform(data) {
		const fields = getFilteredFields(data)
		return applyFilters(fields)
	},
})
formFields.reload()

watch(
	() => employeeAdvance.value.currency,
	(currency) => {
		if (!currency || !formFields.data) return

		updateCurrencyLabels({
			formFields: formFields.data,
			doc: employeeAdvance.value,
			transactionFields: ["paid_amount"],
		})
	},
	{ immediate: true }
)

// helper functions
function getFilteredFields(fields) {
	// reduce noise from the form view by excluding unnecessary fields
	// eg: employee and other details can be fetched from the session user
	const excludeFields = ["naming_series", "base_paid_amount"]
	const extraFields = [
		"employee",
		"employee_name",
		"department",
		"company",
		"more_info_section",
		"pending_amount",
	]

	if (!props.id) excludeFields.push(...extraFields)

	return fields.filter((field) => !excludeFields.includes(field.fieldname))
}

function applyFilters(fields) {
	return fields.map((field) => {
		if (field.fieldname === "advance_account") {
			if (!employeeAdvance.value.currency) return field

			field.linkFilters = {
				root_type: "Asset",
				is_group: 0,
				account_type: "Receivable",
				account_currency: ["in", [employeeAdvance.value.currency]],
				company: employeeAdvance.value.company,
			}
		}

		return field
	})
}

function validateForm() {}
</script>