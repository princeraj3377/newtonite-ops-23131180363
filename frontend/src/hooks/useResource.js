import { useEffect, useState } from 'react'
import { api, getErrorMessage } from '../lib/api'

export function useResource(path, refreshKey = 0) {
  const [revision, setRevision] = useState(0)
  const [result, setResult] = useState(null)
  const key = `${path}:${revision}:${refreshKey}`
  useEffect(() => {
    if (!path) return
    const controller = new AbortController()
    api.get(path, { signal: controller.signal }).then(({ data }) => {
      if (!controller.signal.aborted) setResult({ key, data })
    }).catch((error) => {
      if (!controller.signal.aborted) setResult({ key, error: getErrorMessage(error) })
    })
    return () => controller.abort()
  }, [path, key])
  return {
    data: result?.key === key ? result.data : undefined,
    error: result?.key === key ? result.error : '',
    loading: Boolean(path) && result?.key !== key,
    reload: () => setRevision((value) => value + 1),
  }
}
