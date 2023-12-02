import React from "react";

const title = {
  backgroundColor: 'black',
  color: 'white',
  fontSize: '80px',
  textAlign: 'center',
  fontHeight: '100',
  flex: '10 0 auto',
  width: '100%',
  height: '120px'
}


export default function Display(props) {
  return (<div style={title}>
            <div>{props.text}</div>
          </div>);
}
