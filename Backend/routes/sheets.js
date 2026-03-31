const express = require('express');
const { google } = require('googleapis');
const dotenv = require('dotenv');

dotenv.config();

const router = express.Router();
const SPREADSHEET_ID = '1ObVuVLXelgrKjKTJC3AXpv1YPxbWXO03wt5lXY8I-Po';

let sheetsApi = null;

function getSheetsApi() {
    if (sheetsApi) return sheetsApi;

    if (process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL && process.env.GOOGLE_PRIVATE_KEY) {
        const auth = new google.auth.GoogleAuth({
            credentials: {
                client_email: process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL.trim(),
                private_key: process.env.GOOGLE_PRIVATE_KEY.replace(/\\n/g, '\n'),
            },
            scopes: ['https://www.googleapis.com/auth/spreadsheets.readonly'],
        });
        sheetsApi = google.sheets({ version: 'v4', auth });
        return sheetsApi;
    }

    if (process.env.GOOGLE_API_KEY) {
        const auth = google.auth.fromAPIKey(process.env.GOOGLE_API_KEY);
        sheetsApi = google.sheets({ version: 'v4', auth });
        return sheetsApi;
    }

    console.warn("⚠️ Warning: No Google credentials found in .env");
    return null;
}

async function getDepartments() {
    const api = getSheetsApi();
    if (!api) {
        return ["Sales", "Finance", "HR", "Operations", "Marketing", "Admin", "Manager"];
    }

    try {
        const response = await api.spreadsheets.get({
            spreadsheetId: SPREADSHEET_ID,
        });
        // Return all sheet names (no filtering needed — no Master sheet)
        return response.data.sheets.map(sheet => sheet.properties.title);
    } catch (error) {
        console.error("Error fetching spreadsheet metadata:", error.message);
        return [];
    }
}

async function getSheetData(sheetName) {
    const api = getSheetsApi();
    if (!api) return [];

    try {
        const response = await api.spreadsheets.values.get({
            spreadsheetId: SPREADSHEET_ID,
            range: `'${sheetName}'!A:Z`,
        });

        const rows = response.data.values;
        if (!rows || rows.length === 0) return [];

        // Trim all headers to remove accidental spaces
        const headers = rows[0].map(h => h.trim());

        return rows.slice(1).map(row => {
            const obj = {};
            headers.forEach((header, index) => {
                obj[header] = (row[index] || '').trim();
            });
            return obj;
        });
    } catch (error) {
        console.error(`Error fetching data for sheet "${sheetName}":`, error.message);
        return [];
    }
}

// ✅ ROUTE : GET /api/departments
// Fetch list of all departments/sheets from the spreadsheet
router.get('/departments', async (req, res) => {
    try {
        const departments = await getDepartments();
        res.json(departments);
    } catch (error) {
        console.error('Error in /departments route:', error);
        res.status(500).json({ error: 'Failed to fetch departments' });
    }
});

async function authenticateUser(userId, userName, password, department) {
    const api = getSheetsApi();
    if (!api) {
        if (userId && userName && password) {
            return { userId, userName, department, role: "Employee" };
        }
        return null;
    }

    const data = await getSheetData(department);

    if (data.length === 0) {
        console.warn(`No data found in sheet: ${department}`);
        return null;
    }

    // Debug: log available keys from first row
    console.log(`Sheet "${department}" columns:`, Object.keys(data[0]));

    const user = data.find(row =>
        String(row['User_id']).trim() === String(userId).trim() &&
        String(row['User_name']).toLowerCase().trim() === String(userName).toLowerCase().trim() &&
        String(row['Password']).trim() === String(password).trim()
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

// ✅ ROUTE: POST /api/login
// Authenticate user credentials against the Google Sheets database
router.post('/login', async (req, res) => {
    try {
        const { userId, userName, password, department } = req.body;

        // Validate required fields
        if (!userId || !userName || !password || !department) {
            return res.status(400).json({ 
                success: false, 
                error: 'Missing required fields: userId, userName, password, department' 
            });
        }

        const user = await authenticateUser(userId, userName, password, department);

        if (user) {
            return res.json({
                success: true,
                user: {
                    userName: user.userName,
                    role: user.role,
                    userId: user.userId,
                    department: user.department
                }
            });
        } else {
            return res.status(401).json({
                success: false,
                error: 'Invalid credentials'
            });
        }
    } catch (error) {
        console.error('Error in /login route:', error);
        res.status(500).json({ 
            success: false, 
            error: 'Login failed' 
        });
    }
});

async function getCoursesByDepartment(department) {
    const api = getSheetsApi();
    if (!api) {
        return [
            { id: 1, title: 'Sample Course 1', dept: department, dur: '2 hrs', level: 'Beginner', progress: 0, status: 'Not Started', icon: '📚', bg: 'linear-gradient(135deg, hsl(24 88% 44%), hsl(37 86% 38%))' },
            { id: 2, title: 'Sample Course 2', dept: department, dur: '4 hrs', level: 'Intermediate', progress: 50, status: 'In Progress', icon: '💻', bg: 'linear-gradient(135deg, hsl(220 72% 41%), hsl(213 73% 22%))' }
        ];
    }

    const data = await getSheetData(department);

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

// ✅ ROUTE: GET /api/courses
// Fetch courses for a specific department
router.get('/courses', async (req, res) => {
    try {
        const { department } = req.query;

        if (!department) {
            return res.status(400).json({ 
                error: 'Missing required query parameter: department' 
            });
        }

        const courses = await getCoursesByDepartment(department);
        res.json(courses);
    } catch (error) {
        console.error('Error in /courses route:', error);
        res.status(500).json({ error: 'Failed to fetch courses' });
    }
});

// ✅ HELPER: Create/update Leaves sheet with headers if needed
async function ensureLeavesSheet() {
    const api = getSheetsApi();
    if (!api) return;

    try {
        const response = await api.spreadsheets.values.get({
            spreadsheetId: SPREADSHEET_ID,
            range: `'Leaves'!A1:H1`,
        });

        // If no headers, create them
        if (!response.data.values || !response.data.values[0]) {
            await api.spreadsheets.values.update({
                spreadsheetId: SPREADSHEET_ID,
                range: `'Leaves'!A1:H1`,
                valueInputOption: 'USER_ENTERED',
                resource: {
                    values: [[
                        'Leave_ID',
                        'User_ID',
                        'User_Name',
                        'Department',
                        'Leave_Type',
                        'From_Date',
                        'To_Date',
                        'Days',
                        'Reason',
                        'Status',
                        'Requested_Date',
                        'Approved_By',
                        'Approval_Date',
                        'Comments'
                    ]],
                },
            });
        }
    } catch (error) {
        console.log('Info: Leaves sheet will be created on first request');
    }
}

// ✅ ROUTE: POST /api/leaves - Create a leave request
router.post('/leaves', async (req, res) => {
    try {
        await ensureLeavesSheet();
        
        const { userId, userName, department, leaveType, fromDate, toDate, days, reason } = req.body;

        if (!userId || !userName || !department || !leaveType || !fromDate || !toDate || !days) {
            return res.status(400).json({
                success: false,
                error: 'Missing required fields'
            });
        }

        const api = getSheetsApi();
        if (!api) {
            return res.status(500).json({
                success: false,
                error: 'Google Sheets API not configured'
            });
        }

        const leaveId = `${userId}-${Date.now()}`;
        const requestedDate = new Date().toISOString().split('T')[0];

        const leaveRecord = [
            leaveId,
            userId,
            userName,
            department,
            leaveType,
            fromDate,
            toDate,
            days,
            reason,
            'Pending',
            requestedDate,
            '',
            '',
            ''
        ];

        await api.spreadsheets.values.append({
            spreadsheetId: SPREADSHEET_ID,
            range: `'Leaves'!A2`,
            valueInputOption: 'USER_ENTERED',
            resource: {
                values: [leaveRecord],
            },
        });

        res.json({
            success: true,
            leaveId,
            message: 'Leave request submitted successfully'
        });
    } catch (error) {
        console.error('Error in /leaves POST:', error);
        res.status(500).json({
            success: false,
            error: 'Failed to submit leave request'
        });
    }
});

// ✅ ROUTE: GET /api/leaves - Get leave requests
router.get('/leaves', async (req, res) => {
    try {
        const { userId, department, role } = req.query;

        const api = getSheetsApi();
        if (!api) {
            return res.json([]); // Return empty if API not configured
        }

        const response = await api.spreadsheets.values.get({
            spreadsheetId: SPREADSHEET_ID,
            range: `'Leaves'!A:N`,
        });

        const rows = response.data.values || [];
        if (rows.length === 0) return res.json([]);

        const headers = rows[0].map(h => h.trim());
        const leaves = rows.slice(1).map(row => {
            const obj = {};
            headers.forEach((header, index) => {
                obj[header] = (row[index] || '').trim();
            });
            return obj;
        });

        let filteredLeaves = leaves;

        if (role === 'Manager') {
            // Managers see pending leaves from their department to approve
            filteredLeaves = leaves.filter(l => 
                l['Department'] === department && l['Status'] === 'Pending'
            );
        } else {
            // Employees see only their own leaves
            filteredLeaves = leaves.filter(l => l['User_ID'] === userId);
        }

        res.json(filteredLeaves);
    } catch (error) {
        console.error('Error in /leaves GET:', error);
        res.status(500).json({ error: 'Failed to fetch leaves' });
    }
});

// ✅ ROUTE: PATCH /api/leaves/:id - Approve/Reject leave
router.patch('/leaves/:id', async (req, res) => {
    try {
        const { id } = req.params;
        const { action, approvedBy, comments } = req.body;

        if (!['approve', 'reject'].includes(action)) {
            return res.status(400).json({
                success: false,
                error: 'Invalid action. Must be "approve" or "reject"'
            });
        }

        const api = getSheetsApi();
        if (!api) {
            return res.status(500).json({
                success: false,
                error: 'Google Sheets API not configured'
            });
        }

        const response = await api.spreadsheets.values.get({
            spreadsheetId: SPREADSHEET_ID,
            range: `'Leaves'!A:N`,
        });

        const rows = response.data.values || [];
        const headers = rows[0].map(h => h.trim());
        
        let leaveIndex = -1;
        for (let i = 1; i < rows.length; i++) {
            const leaveId = (rows[i][0] || '').trim();
            if (leaveId === id) {
                leaveIndex = i;
                break;
            }
        }

        if (leaveIndex === -1) {
            return res.status(404).json({
                success: false,
                error: 'Leave request not found'
            });
        }

        const approvalDate = new Date().toISOString().split('T')[0];
        const status = action === 'approve' ? 'Approved' : 'Rejected';

        const updatedRow = [...rows[leaveIndex]];
        updatedRow[9] = status; // Status column
        updatedRow[11] = approvedBy; // Approved_By
        updatedRow[12] = approvalDate; // Approval_Date
        updatedRow[13] = comments || ''; // Comments

        await api.spreadsheets.values.update({
            spreadsheetId: SPREADSHEET_ID,
            range: `'Leaves'!A${leaveIndex + 1}:N${leaveIndex + 1}`,
            valueInputOption: 'USER_ENTERED',
            resource: {
                values: [updatedRow],
            },
        });

        res.json({
            success: true,
            message: `Leave request ${status.toLowerCase()} successfully`,
            leaveId: id,
            status
        });
    } catch (error) {
        console.error('Error in /leaves PATCH:', error);
        res.status(500).json({
            success: false,
            error: 'Failed to update leave status'
        });
    }
});

// Export the router
module.exports = router;