import TopBar from '../components/layout/TopBar'
import ProvisionForm from '../components/provision/ProvisionForm'

export default function Provision() {
  return (
    <div>
      <TopBar title="Provision VM" />
      <div style={{ padding: 24, maxWidth: 1100 }}>
        <ProvisionForm />
      </div>
    </div>
  )
}
