const express = require('express');
const { spawn } = require('child_process');
const path = require('path');
const dotenv = require('dotenv');

dotenv.config();

const router = express.Router();

/**
 * Helper to run Python Monitoring Agent
 */
function runMonitoringAgent(userMetadata) {
  return new Promise((resolve, reject) => {
    const agentPath = path.join(__dirname, '../agents/Monitoring_agent.py');
    const pythonProcess = spawn('python', [agentPath], {
      cwd: path.join(__dirname, '../agents'),
      env: { ...process.env },
    });

    let stdout = '';
    let stderr = '';

    pythonProcess.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    pythonProcess.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    pythonProcess.on('close', (code) => {
      if (code !== 0) {
        console.error('Monitoring Agent Error:', stderr);
        reject(new Error(stderr || 'Monitoring agent failed'));
      } else {
        try {
          const result = JSON.parse(stdout);
          resolve(result);
        } catch (e) {
          console.error('Failed to parse agent output:', stdout);
          reject(new Error('Invalid agent response'));
        }
      }
    });

    pythonProcess.on('error', (err) => {
      reject(err);
    });
  });
}

/**
 * POST /api/monitoring/insights
 * Get daily insights, metrics, and greeting for a user
 */
router.post('/monitoring/insights', async (req, res) => {
  try {
    const { user_id, name, role, department } = req.body;

    if (!user_id || !name) {
      return res.status(400).json({
        success: false,
        error: 'user_id and name are required',
      });
    }

    // Run the monitoring agent
    const report = await runMonitoringAgent({
      user_id,
      name,
      role: role || 'Employee',
      department: department || 'General',
    });

    // Extract insights and greeting from report
    const insights = report.analysis?.insights || [];
    const greeting = report.greeting || `Namaste ${name?.split(' ')[0]} 🙏 I'm your personal Monitoring AI.`;
    const metrics = report.metrics || {};
    const recommendations = report.analysis?.recommendations || [];

    res.json({
      success: true,
      user_id,
      insights,
      greeting,
      metrics,
      recommendations,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error('Monitoring insights error:', error);
    
    // Return a fallback response instead of erroring
    const { user_id, name } = req.body;
    res.json({
      success: true,
      user_id,
      insights: [
        {
          type: 'tip',
          text: '💡 Pro tip: Schedule 30-min daily learning sessions for consistent progress',
        },
      ],
      greeting: `Namaste ${name?.split(' ')[0] || 'there'} 🙏 I'm your personal Monitoring AI.`,
      metrics: {
        courses_completed: 0,
        courses_in_progress: 0,
        quiz_average: 0,
        total_hours: 0,
        current_streak: 0,
        department_rank: 0,
        goals_completed: 0,
      },
      recommendations: [
        'Focus on your core learning goals',
        'Practice consistently for better results',
      ],
      timestamp: new Date().toISOString(),
    });
  }
});

/**
 * POST /api/monitoring/chat
 * Chat with Monitoring AI - get AI responses about user's learning journey
 *
 * Body: {
 *   user_id: string,
 *   name: string,
 *   role: string,
 *   department: string,
 *   message: string,
 *   history?: Array<{role, text}>
 * }
 */
router.post('/monitoring/chat', async (req, res) => {
  try {
    const { user_id, name, role, department, message, history } = req.body;

    if (!user_id || !message) {
      return res.status(400).json({
        success: false,
        error: 'user_id and message are required',
      });
    }

    // Generate AI response based on the user's message
    // For now, return contextual responses based on message keywords
    const reply = generateMonitoringResponse(
      message,
      {
        name: name || 'User',
        role: role || 'Employee',
        department: department || 'General',
      },
      history || []
    );

    res.json({
      success: true,
      user_id,
      reply,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error('Monitoring chat error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to process chat message',
      timestamp: new Date().toISOString(),
    });
  }
});

/**
 * Generate contextual responses for monitoring chat
 * (In production, this should integrate with a real AI/LLM)
 */
function generateMonitoringResponse(message, userInfo, history) {
  const lowerMsg = message.toLowerCase();

  // Progress-related
  if (lowerMsg.includes('progress') || lowerMsg.includes('how am i')) {
    return `Hi ${userInfo.name}! 📊 Based on your learning journey, I see you're building solid momentum. Keep adding consistent effort to your courses. Next week, focus on the topics you found challenging. You're doing great!`;
  }

  // Course recommendations
  if (lowerMsg.includes('recommend') || lowerMsg.includes('course')) {
    return `Great question! 📚 For a ${userInfo.role} in ${userInfo.department}, I'd recommend focusing on:
1. Advanced ${userInfo.department}-specific courses
2. Skill-gap closure courses
3. Professional development certifications

Which area interests you most?`;
  }

  // Quiz/Performance
  if (lowerMsg.includes('quiz') || lowerMsg.includes('score') || lowerMsg.includes('perform')) {
    return `Your quiz performance shows great potential! 🎯 I noticed slower improvements in certain topics. Try these strategies:
- Practice quizzes daily (even 15 mins helps)
- Review incorrect answers deeply
- Form study groups with peers

Would you like specific topic recommendations?`;
  }

  // Goals
  if (lowerMsg.includes('goal') || lowerMsg.includes('target') || lowerMsg.includes('plan')) {
    return `🎯 Let's build a smart learning plan together! Tell me:
1. Your main career goal this quarter
2. 2-3 top skills you want to develop
3. Time you can dedicate weekly

Then I'll create a personalized roadmap just for you!`;
  }

  // Motivation/Encouragement
  if (lowerMsg.includes('motivation') || lowerMsg.includes('stuck') || lowerMsg.includes('help')) {
    return `I hear you! 💪 Learning marathons have ups and downs. Here's what helps:
- Break big goals into tiny daily wins
- Celebrate small victories
- Remember why you started this journey

You've got this! What's one thing you can accomplish today? 🌟`;
  }

  // Skills/Department-specific
  if (lowerMsg.includes('skill') || lowerMsg.includes('gap')) {
    return `🔍 Skill gap analysis for ${userInfo.role}s in ${userInfo.department}:

Key gaps to close:
1. Advanced technical skills in core tools
2. Leadership & communication in your field
3. Industry-specific certifications

Want me to recommend courses for any of these?`;
  }

  // Rank/Competition
  if (lowerMsg.includes('rank') || lowerMsg.includes('higher') || lowerMsg.includes('competition')) {
    return `📈 To climb the ranks in your department:
1. Complete more advanced courses (1-2 per week)
2. Maintain consistent learning streaks (30+ days)
3. Score 85%+ on all quizzes
4. Help peers (mentoring boosts your ranking)

You're on a great path! Keep going! 🚀`;
  }

  // Default helpful response
  return `Hi ${userInfo.name}! I'm here to help you grow. I can help with:
- 📊 Progress analysis and insights
- 📚 Course recommendations for your department
- 🎯 Goal setting and learning plans
- 📈 Performance tips and strategies
- 💪 Motivation when you're stuck
- 🏆 Ranking improvements

What would you like to focus on today?`;
}

/**
 * GET /api/monitoring/report
 * Get comprehensive weekly report for a user
 */
router.get('/monitoring/report/:userId', async (req, res) => {
  try {
    const { userId } = req.params;

    // TODO: Fetch actual user data from database
    const mockUserData = {
      id: userId,
      name: 'User',
      role: 'Employee',
      department: 'General',
    };

    const report = await runMonitoringAgent(mockUserData);

    res.json({
      success: true,
      report,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error('Monitoring report error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to generate report',
      timestamp: new Date().toISOString(),
    });
  }
});

module.exports = router;
