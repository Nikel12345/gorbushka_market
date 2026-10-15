export function FieldError({ messages }: { messages?: string[] }) {
  if (!messages?.length) return null
  return (
    <div className="field-error" role="alert">
      {messages.map((message) => (
        <div key={message}>{message}</div>
      ))}
    </div>
  )
}
