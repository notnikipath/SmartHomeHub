import React from "react";

export function TaskBoard({ devices }) {
  if (!devices?.length) {
    return <div className="empty-board">No devices available for this home.</div>;
  }

  const byRoom = devices.reduce((acc, device) => {
    const room = device.room || "unknown";
    if (!acc[room]) {
      acc[room] = [];
    }
    acc[room].push(device);
    return acc;
  }, {});

  return (
    <section className="room-grid">
      {Object.entries(byRoom).map(([room, items]) => (
        <article className="room-card" key={room}>
          <div className="room-head">
            <p className="module-kicker">Room</p>
            <h3>{room.replaceAll("_", " ")}</h3>
          </div>
          <div className="stack-list">
            {items.map((device) => (
              <div className="stack-item" key={device.device_id}>
                <div>
                  <p className="stack-title">{device.name}</p>
                  <p className="stack-sub">
                    {device.brand} {device.model}
                  </p>
                </div>
                <span>{device.status}</span>
              </div>
            ))}
          </div>
        </article>
      ))}
    </section>
  );
}