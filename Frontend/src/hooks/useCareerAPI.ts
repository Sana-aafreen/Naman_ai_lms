import { useState } from 'react'
import { apiGet, apiPost } from '../lib/api'

export function useCareerAPI() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchJobs = async (filters: Record<string, unknown>) => {
    setLoading(true)
    setError(null)
    try {
      const data = await apiGet<unknown>('/api/career/jobs')
      return data
    } catch (err: unknown) {
      setError((err instanceof Error ? err.message : String(err)) || "Failed to fetch jobs")
      throw err
    } finally {
      setLoading(false)
    }
  }

  const applyToJob = async (jobId: string, empId: string, coverNote: string) => {
    setLoading(true)
    setError(null)
    try {
      await apiPost(`/api/career/jobs/${jobId}/apply`, { job_id: jobId, employee_id: empId, cover_note: coverNote })
    } catch (err: unknown) {
      setError((err instanceof Error ? err.message : String(err)) || "Failed to apply")
      throw err
    } finally {
      setLoading(false)
    }
  }

  const streamInterviewReply = async (params: Record<string, unknown>, onChunk: (c: string) => void, onDone: () => void) => {
    setLoading(true)
    setError(null)
    try {
      const response = await apiPost<{reply: string}>('/api/career/interview/stream', params)
      const reply = response.reply || ""
      const chunks = reply.split(" ")
      for (const c of chunks) {
        await new Promise(r => setTimeout(r, 50))
        onChunk(c + " ")
      }
    } catch (err: unknown) {
      setError((err instanceof Error ? err.message : String(err)) || "Chat failed")
      onChunk("Sorry, I am facing some issues connecting right now.")
    } finally {
      setLoading(false)
      onDone()
    }
  }

  const assessAnswer = async (params: Record<string, unknown>) => {
    setLoading(true)
    setError(null)
    try {
      const data = await apiPost<unknown>('/api/career/interview/assess', params)
      return data
    } catch (err: unknown) {
      setError((err instanceof Error ? err.message : String(err)) || "Assessment failed")
      throw err
    } finally {
      setLoading(false)
    }
  }

  const optimizeATS = async (params: Record<string, unknown>) => {
    setLoading(true)
    setError(null)
    try {
      const data = await apiPost<unknown>('/api/career/cv/optimize-ats', params)
      return data
    } catch (err: unknown) {
      setError((err instanceof Error ? err.message : String(err)) || "ATS optimization failed")
      throw err
    } finally {
      setLoading(false)
    }
  }

  const downloadCVPDF = async (cvData: Record<string, unknown>) => {
    setLoading(true)
    setError(null)
    try {
      await apiPost('/api/career/cv/download', { cvData })
      alert("PDF Download Mock Successful!")
    } catch (err: unknown) {
      setError((err instanceof Error ? err.message : String(err)) || "PDF download failed")
      throw err
    } finally {
      setLoading(false)
    }
  }

  return { loading, error, fetchJobs, applyToJob, streamInterviewReply, assessAnswer, optimizeATS, downloadCVPDF }
}
