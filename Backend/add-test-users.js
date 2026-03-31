#!/usr/bin/env node

/**
 * Add Test Users to Google Sheets (Sales Sheet)
 * This script adds sample user data to your Google Sheets
 */

const { google } = require('googleapis');
require('dotenv').config();

const SPREADSHEET_ID = '1ObVuVLXelgrKjKTJC3AXpv1YPxbWXO03wt5lXY8I-Po';
const SHEET_NAME = 'Sales';

const testUsers = [
  ['EMP001', 'Naman', 'naman123', 'Admin', 'naman@namandarshan.com'],
  ['EMP002', 'John Doe', 'john123', 'Employee', 'john@namandarshan.com'],
  ['EMP003', 'Sarah Smith', 'sarah123', 'Manager', 'sarah@namandarshan.com'],
  ['EMP004', 'Priya Sharma', 'priya123', 'Employee', 'priya@namandarshan.com'],
  ['EMP005', 'Raj Kumar', 'raj123', 'Employee', 'raj@namandarshan.com'],
];

async function addTestUsers() {
  console.log('\n🧪 Adding Test Users to Google Sheets...\n');

  try {
    let auth;
    
    // Try service account first
    if (process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL && process.env.GOOGLE_PRIVATE_KEY) {
      const email = process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL.trim();
      const key = process.env.GOOGLE_PRIVATE_KEY.replace(/\\n/g, '\n');
      
      console.log(`📧 Using Service Account: ${email}`);
      
      auth = new google.auth.GoogleAuth({
        credentials: {
          client_email: email,
          private_key: key,
          type: 'service_account',
        },
        scopes: ['https://www.googleapis.com/auth/spreadsheets'],
      });
    } else if (process.env.GOOGLE_API_KEY) {
      console.log('🔑 Using API Key');
      auth = google.auth.fromAPIKey(process.env.GOOGLE_API_KEY);
    } else {
      throw new Error('No Google credentials found in .env');
    }

    const sheets = google.sheets({ version: 'v4', auth });

    // Check sheet exists and has headers
    console.log('📋 Checking sheet structure...');
    let getResponse;
    try {
      getResponse = await sheets.spreadsheets.values.get({
        spreadsheetId: SPREADSHEET_ID,
        range: `'${SHEET_NAME}'!A1:E1`,
      });
    } catch (e) {
      console.error(`❌ Error: Cannot access sheet "${SHEET_NAME}"`);
      throw e;
    }

    if (!getResponse.data.values || !getResponse.data.values[0]) {
      console.log('⚠️  Sheet is empty or missing headers');
      console.log('📝 Creating headers: User_id | User_name | Password | Role | Email\n');
      
      // Create headers
      await sheets.spreadsheets.values.update({
        spreadsheetId: SPREADSHEET_ID,
        range: `'${SHEET_NAME}'!A1:E1`,
        valueInputOption: 'USER_ENTERED',
        resource: {
          values: [['User_id', 'User_name', 'Password', 'Role', 'Email']],
        },
      });
    }

    // Clear existing data (keep header)
    console.log('🧹 Clearing old test data from Sales sheet...');
    try {
      await sheets.spreadsheets.values.clear({
        spreadsheetId: SPREADSHEET_ID,
        range: `'${SHEET_NAME}'!A2:Z1000`,
      });
    } catch (e) {
      console.log('(First run, no data to clear)');
    }

    // Add the test users
    console.log('➕ Adding test users...');
    const appendResponse = await sheets.spreadsheets.values.append({
      spreadsheetId: SPREADSHEET_ID,
      range: `'${SHEET_NAME}'!A2`,
      valueInputOption: 'USER_ENTERED',
      resource: {
        values: testUsers,
      },
    });

    console.log('\n✅ Successfully added test users!\n');
    console.log('📊 Sample Login Credentials:');
    console.log('─'.repeat(65));
    testUsers.forEach((user, index) => {
      const id = user[0].padEnd(4);
      const name = user[1].padEnd(20);
      const pwd = user[2].padEnd(12);
      console.log(`${index + 1}. ID: ${id} | Name: ${name} | Pwd: ${pwd} | Role: ${user[3]}`);
    });
    console.log('─'.repeat(65));
    console.log('\n🎯 Try logging in with:');
    console.log('   User ID: EMP001');
    console.log('   User Name: Naman');
    console.log('   Password: naman123');
    console.log('   Department: Sales');
    console.log('   Role: Employee\n');

  } catch (error) {
    console.error('\n❌ ERROR:', error.message);
    console.error('\nTroubleshooting:');
    console.error('1. Check Backend/.env file has GOOGLE_API_KEY or SERVICE_ACCOUNT credentials');
    console.error('2. Check Google Service Account has editor access to the sheet');
    console.error('3. Make sure Sales sheet exists in your Google Sheet');
    console.error('4. Run from Backend directory: node add-test-users.js\n');
    process.exit(1);
  }
}

addTestUsers();

