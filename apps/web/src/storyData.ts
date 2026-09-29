export const places:Record<string,{name:string;short:string;district:string;person:string;job:string}>={
 A:{name:'Madhavapur Primary Health Centre',short:'Madhavapur',district:'Riverbend district',person:'Anitha Rao',job:'Pharmacist'},
 B:{name:'Sevanagar Primary Health Centre',short:'Sevanagar',district:'Riverbend district',person:'Ravi Kumar',job:'Pharmacist'},
 C:{name:'Anandapur Community Health Centre',short:'Anandapur',district:'Hillview district',person:'Farah Begum',job:'Pharmacist'},
 D:{name:'Riverbend District Medicine Store',short:'Riverbend store',district:'Riverbend district',person:'Suresh Das',job:'Store manager'},
 E:{name:'Padmapur Primary Health Centre',short:'Padmapur',district:'Riverbend district',person:'Meena Devi',job:'Pharmacist'},
 F:{name:'Neemgaon Primary Health Centre',short:'Neemgaon',district:'Hillview district',person:'Arun Das',job:'Pharmacist'},
 G:{name:'Mallipur Primary Health Centre',short:'Mallipur',district:'Hillview district',person:'Lakshmi Sen',job:'Pharmacist'},
 H:{name:'Hillview District Medicine Store',short:'Hillview store',district:'Hillview district',person:'Joseph Paul',job:'Store manager'}
};
export const people={
 reporter:{name:'Anitha Rao',initials:'AR',title:'Pharmacist at Madhavapur',task:'Counts the medicine on the shelf and reports what the centre has.',role:'custodian',district:'D1'},
 planner:{name:'Vikram Sen',initials:'VS',title:'Medicine supply coordinator',task:'Finds a centre that can help without leaving its own patients short.',role:'planner',district:'D1'},
 recipientApprover:{name:'Dr Kavya Rao',initials:'KR',title:'Riverbend district health officer',task:'Confirms that Madhavapur needs this medicine.',role:'approver',district:'D1'},
 donorApprover:{name:'Dr Imran Ali',initials:'IA',title:'Hillview district health officer',task:'Checks that Anandapur can safely spare the medicine.',role:'approver',district:'D2'},
 sender:{name:'Farah Begum',initials:'FB',title:'Pharmacist at Anandapur',task:'Packs the approved tablets and records that they have left the centre.',role:'custodian',district:'D2'},
 receiver:{name:'Anitha Rao',initials:'AR',title:'Pharmacist at Madhavapur',task:'Counts the tablets that arrived and confirms the delivery.',role:'receiver',district:'D1'}
};
export const steps=['Count medicine','Find help','Get permission','Send the box','Confirm arrival'];
