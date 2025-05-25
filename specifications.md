# Arraiá da Laura – RSVP System Specifications

## Project Context

This project is a web-based RSVP system for a private party ("Arraiá da Laura"), designed to collect attendance information, dietary preferences, and payment confirmation from invited guests. The system must be accessible, reliable, and easy to use on both desktop and mobile devices.

## User Flow

1. **City Selection**  
   User selects their city of origin (either "São José dos Campos" or "Taubaté").

2. **Group Selection**  
   User selects which group they belong to (groups are specific to each city).

3. **Number of People**  
   User selects how many people they are confirming (including themselves, family members, or significant others; “convidado não convida”).

4. **Names & Vegetarian Option**  
   For each person, the user enters a name and marks if they are vegetarian.

5. **Contact Phone Number**  
   User provides a phone number for contact.

6. **Pix Payment**  
   User is informed of the cost (R$15 per person) and shown a Pix QR code generated with:
   - A constant Pix key (set in config)
   - Total value (15 * number of confirmed people)
   - Description: names of all confirmed people

   User clicks “Fiz o Pix!” after completing payment in their banking app.

7. **Confirmation**  
   User sees a thank you message and confirmation that their RSVP was recorded.

## Technical Specifications

- **Backend**: Python 3.x, Flask
- **Frontend**: Jinja2 templates, HTML/CSS (visuals are placeholders)
- **Data Storage**: Google Sheets (via Google Sheets API)
- **QR Code**: Generated using Python libraries (`qrcode`, `pillow`)
- **Languages**: All user-facing text in Brazilian Portuguese
- **Cities/Groups**: Hardcoded lists in the backend
- **Navigation**: Linear, with “back” navigation enabled until payment is confirmed
- **Deployment**: Flask app suitable for deployment on PythonAnywhere, Heroku, or similar
- **Security**: No authentication, anti-spam, or email/SMS confirmation at this stage

## Data Collected

- City
- Group
- Number of people
- For each person: name, vegetarian (yes/no)
- Phone number
- Pix payment value
- Pix description (names)
- Timestamp

## Google Sheets Structure

Each RSVP is a new row with columns:
- Timestamp
- City
- Group
- Number of people
- Names (comma-separated)
- Vegetarian (comma-separated, or per person)
- Phone number
- Payment value
- Pix description

## Future Improvements

- Visual/animation enhancements after payment confirmation
- Custom backgrounds and styles
- Admin interface for RSVP management

## Out of Scope

- Payment verification
- Email/SMS confirmation
- Anti-spam measures
- User authentication

---