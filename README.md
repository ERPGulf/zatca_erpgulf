
Saudi Arabian E-Invoicing (ZATCA Phase-2) – A Frappe ERPNext App

A Frappe ERPNext app for businesses in Saudi Arabia, ensuring compliance with ZATCA Phase-2 e-invoicing regulations.

🚀 Features

✅ Compliance with ZATCA E-Invoicing Phase-2 <br>
✅ Integration with ZATCA APIs for clearance & reporting <br>
✅ Automatic CSR generation & compliance checks<br>
✅ Secure authentication & token management<br>
✅ Invoice submission for clearance & reporting<br>
✅ Support for standard invoices, credit notes, debit notes <br>
✅ Retrieve and attach QR Codes to invoices<br>
✅ Logging for audit trails & error handling<br>
✅ Reports to compare invoices with ZATCA portal statistics <br>

🔹 Additional Features

### Credit Note for Legacy System Invoices

Users can create and submit credit notes to ZATCA for invoices that were generated outside the current ERPNext system (legacy invoices).

To enable this feature:

* Go to **Company → ZATCA Settings**.
* Enable the checkbox **"Allow Credit-note without Original Invoice in the System"**.
* Enter the original legacy invoice number in **"Return Against for ZATCA"** on the Sales Invoice.

This allows the credit note to be submitted to ZATCA even when the original invoice does not exist in ERPNext.

### Skip ERPNext Credit Note Validations

A new checkbox is available on the **Sales Invoice**:

**"Skip Validation for Credit Note"**

When enabled, ERPNext validations related to credit notes and the **Return Against** reference are bypassed. This allows organizations to process special business scenarios and submit the document to ZATCA without standard ERPNext return validations.

### Profit Margin Method (PMM)

A new checkbox is available on the **Sales Invoice**:

**"ZATCA PMM (Profit Margin Method)"**

When this checkbox is selected:

* The Sales Invoice is submitted normally within ERPNext.
* The invoice is **not submitted to ZATCA**.
* No ZATCA clearance or reporting process is triggered for that invoice.

This option is intended for transactions that fall under the Profit Margin Method (PMM) treatment and require special handling.

🔹Version 3.0 Enhancements

✨ Saves XML files directly without temporary storage → frees up hard disk space
✨ Improved performance for invoice generation & submission
✨ Enhanced error handling and logging for failed submissions
✨ Optimized QR code generation and attachment
✨ Updated compliance checks for latest ZATCA regulations

🔹 Compatibility<br>
🌐 ERPNext Version13, 14 and 15<br>
🖥️ Platforms	Ubuntu, Centos, Oracle Linux<br>

🛠 Installation Configuration & Setup

🔹 For Frappe Cloud Users

Frappe Cloud users can install the app directly from the Marketplace.

🔹 Build cloud server in Jeddah or Riyadh with  ERPNext & Zatca using Claudion https://saudi.claudion.com/onboarding 


🔹 For Self-Hosted ERPNext Users

Follow the standard Frappe app installation process:

# Get the app from GitHub
bench get-app https://github.com/ERPGulf/zatca_erpgulf.git

# Install the app on your site
bench --site yoursite.erpgulf.com install-app zatca_erpgulf

# Apply necessary migrations
bench --site yoursite.erpgulf.com migrate

# Restart bench or supervisor
bench restart 
or
sudo service supervisor restart


🔹 Verify Installation<br>
	1.	Login to ERPNext.<br>
	2.	Navigate to Help → About.<br>
	3.	Ensure the ZATCA app is listed.<br>

📈 Project Status

Feature	Details
🔓 License	MIT (Or another license)<br>
🌍 Website	https://erpgulf.com<br>
🛠 Maintenance<br>	✅ Actively Maintained<br>
🔄 PRs Welcome	<br>✅ Contributions Encouraged<br>
🏆 Open Source	✅

📺 Video Tutorial  https://www.youtube.com/watch?v=P0ChplXoKYg<br>
📺 Detailed documentation  https://docs.claudion.com/zatca%20pdf-a3<br>
📺 Handling Error messages from ZATCA  https://docs.claudion.com/Claudion-Docs/ErrorMessage1<br>
📺 Coding policy  https://docs.claudion.com/Claudion-Docs/Coding%20Policy<br>

🎥 Watch our step-by-step tutorial on YouTube:

🌟 Development & Contributions

We welcome contributions! To contribute:<br>
	1.	Fork this repository. <br>
	2.	Make your changes (improve the code, add features, fix bugs).<br>
	3.	Submit a Pull Request for review.<br>
	4.	If you find issues, please report them via the Issues section.<br>

Your contributions help make this project better! 🙌

📩 Support & Customization

For implementation support or customization, contact:
📧 support@ERPGulf.com

👥 Social

🚀 Now you’re ready to be fully ZATCA-compliant! 🎯
