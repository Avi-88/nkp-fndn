import { useState } from "react"; from 'react'

let events = null;

function BastionTerminal() {

    const [commandOut , setCommandOut] = useState([])
    const [isActive, setIsActive] = useState(false)

  return (
    <div>BastionTerminal</div>
  )
}

export default BastionTerminal