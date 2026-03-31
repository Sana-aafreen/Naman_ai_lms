const { google } = require('googleapis');
const dotenv = require('dotenv');

dotenv.config();

// The Google Sheet ID from the provided URL
const SPREADSHEET_ID = '1ObVuVLXelgrKjKTJC3AXpv1YPxbWXO03wt5lXY8I-Po';

let sheetsApi = null;

function getSheetsApi() {
    if (sheetsApi) return sheetsApi;

    // Initialize Auth
    if (process.env.GOOGLE_API_KEY) {
        const auth = google.auth.fromAPIKey(process.env.GOOGLE_API_KEY);
        sheetsApi = google.sheets({ version: 'v4', auth });
        return sheetsApi;
    } else if (process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL && process.env.GOOGLE_PRIVATE_KEY) {
        const auth = new google.auth.GoogleAuth({
            credentials: {
                client_email: process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL,
                private_key: process.env.GOOGLE_PRIVATE_KEY.replace(/\\n/g, '\n'),
            },
            scopes: ['https://www.googleapis.com/auth/spreadsheets.readonly'],
        });
        sheetsApi = google.sheets({ version: 'v4', auth });
        return sheetsApi;
    }

    console.warn("⚠️ Warning: No Google API Key or Service Account provided in .env.");
    return null;
}

async function getDepartments() {
    const api = getSheetsApi();
    if (!api) {
        // Fallback Mock Data if no credentials available
        return ["Sales", "Ops", "Sewa", "Puja & Pandit", "Logistics", "Content & SEO", "Tech & Stream", "Finance"];
    }

    try {
        const response = await api.spreadsheets.get({
            spreadsheetId: SPREADSHEET_ID,
        });
        // Each sheet name represents a department
        return response.data.sheets.map(sheet => sheet.properties.title).filter(title => title !== 'Master');
    } catch (error) {
        console.error("Error fetching spreadsheets metadata:", error);
        return [];
    }
}

async function getSheetData(sheetName) {
    const api = getSheetsApi();
    if (!api) return [];

    try {
        const response = await api.spreadsheets.values.get({
            spreadsheetId: SPREADSHEET_ID,
            range: `'${sheetName}'!A:Z`, // Fetch entire sheet
        });

        const rows = response.data.values;
        if (!rows || rows.length === 0) return [];

        // Convert array of arrays to array of objects using exactly the first row as headers
        const headers = rows[0].map(h => h.trim());
        return rows.slice(1).map(row => {
            const obj = {};
            headers.forEach((header, index) => {
                obj[header] = row[index] || '';
            });
            return obj;
        });
    } catch (error) {
        console.error(`Error fetching data for ${sheetName}:`, error);
        return [];
    }
}

async function authenticateUser(userId, userName, password, department) {
    if (!getSheetsApi()) {
        // Mock Authentication for seamless testing when no API key
        if (userId && userName && password) {
            return {
                userId,
                userName,
                department,
                role: "Employee" // default role
            };
        }
        return null;
    }

    // Fetch from the specific department tab
    const data = await getSheetData(department);

    // Find a matching user 
    // We expect columns like User_id, User_name, Password
    const user = data.find(row =>
        String(row['User_id']) === String(userId) &&
        String(row['User_name']).toLowerCase() === String(userName).toLowerCase() &&
        String(row['Password']) === String(password)
    );

    if (user) {
        return {
            userId: user['User_id'],
            userName: user['User_name'],
            department,
            role: user['Role'] || "Employee"
        };
    }

    return null;
}

async function getCoursesByDepartment(department) {
    if (!getSheetsApi()) {
        // Fallback mock courses if no Google API credentials
        return [
            { id: 1, title: 'Sample Course 1', dept: department, dur: '2 hrs', level: 'Beginner', progress: 0, status: 'Not Started', icon: '📚', bg: 'linear-gradient(135deg, hsl(24 88% 44%), hsl(37 86% 38%))' },
            { id: 2, title: 'Sample Course 2', dept: department, dur: '4 hrs', level: 'Intermediate', progress: 50, status: 'In Progress', icon: '💻', bg: 'linear-gradient(135deg, hsl(220 72% 41%), hsl(213 73% 22%))' }
        ];
    }

    const data = await getSheetData(department);

    // Assuming courses are rows where 'Course Name' exists
    // Or they could just be rows that have 'Course_Name' or 'Title' instead of 'User_id'
    const courses = data.filter(row => row['Course Name'] || row['Course_Name'] || row['Title']);

    return courses.map((c, i) => ({
        id: c['ID'] || c['Course_ID'] || (i + 1),
        title: c['Course Name'] || c['Course_Name'] || c['Title'],
        dept: department,
        dur: c['Duration'] || c['Course Duration'] || '2 hrs',
        level: c['Level'] || 'Beginner',
        progress: parseInt(c['Progress']) || 0,
        status: c['Status'] || 'Not Started',
        icon: c['Icon'] || '📚',
        bg: c['Bg_Gradient'] || 'linear-gradient(135deg, hsl(24 88% 44%), hsl(37 86% 38%))'
    }));
}

module.exports = {
    getDepartments,
    authenticateUser,
    getCoursesByDepartment
};
