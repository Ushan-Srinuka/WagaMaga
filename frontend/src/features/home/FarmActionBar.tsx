import { useState } from 'react'
import { Link, Navigate } from 'react-router'
import {
  cropName,
  type Crop,
  type Cultivation,
  type Farm,
  type Page,
} from '../../lib/farms'
import { Pagination, ReadState } from '../farms/RecordUI'
import { useRecord } from '../farms/record-hooks'

type FarmAction = 'note' | 'planner' | 'chat'
const titles = {
  note: 'Add a field note',
  planner: 'Planner',
  chat: 'Ask about my crop',
}

export default function FarmActionBar({ action }: { action: FarmAction }) {
  const [page, setPage] = useState(1)
  const farms = useRecord<Page<Farm>>(`/farms?status=active&page=${page}`)
  const [chosen, setChosen] = useState<Farm | null>(null)
  const farm =
    chosen ?? (farms.data?.total === 1 ? farms.data.items[0] : undefined)
  return (
    <div className="farm-records">
      <Link to="/">← Home</Link>
      <h1>{titles[action]}</h1>
      {!farms.data ? (
        <ReadState {...farms} retry={farms.reload} />
      ) : farm ? (
        <>
          {chosen && (
            <button onClick={() => setChosen(null)}>Change farm</button>
          )}
          <CropChoices key={farm.id} farm={farm} action={action} />
        </>
      ) : farms.data.total === 0 ? (
        <section className="panel">
          <p>Add a farm and a crop to get started.</p>
          <Link to="/farms/new">Add your first farm</Link>
        </section>
      ) : (
        <section className="panel">
          <h2>Choose your farm</h2>
          <ul className="record-rows">
            {farms.data.items.map((item) => (
              <li key={item.id}>
                <button onClick={() => setChosen(item)}>
                  {item.name} · {item.location}
                </button>
              </li>
            ))}
          </ul>
          {farms.data.total > farms.data.page_size && (
            <Pagination page={page} change={setPage} result={farms.data} />
          )}
        </section>
      )}
    </div>
  )
}

function CropChoices({ farm, action }: { farm: Farm; action: FarmAction }) {
  const [page, setPage] = useState(1)
  const types = useRecord<Page<Crop>>('/crop-types?page_size=100')
  const path = `/farms/${farm.id}/cultivations`
  const records = useRecord<Page<Cultivation>>(
    `${path}?status=active&page=${page}`,
  )
  if (!records.data || !types.data)
    return (
      <ReadState
        loading={records.loading || types.loading}
        error={records.error ?? types.error}
        retry={() => {
          records.reload()
          types.reload()
        }}
      />
    )
  const chilliId = types.data.items.find((type) => type.code === 'chilli')?.id
  const choices = records.data.items.filter(
    (crop) => action !== 'chat' || crop.crop_type_id === chilliId,
  )
  function destination(crop: Cultivation) {
    const query = action === 'note' ? 'view=notes&observe=1' : `view=${action}`
    return `${path}/${crop.id}?${query}`
  }
  if (records.data.total === 1 && choices.length === 1)
    return <Navigate replace to={destination(choices[0])} />
  return (
    <section className="panel">
      <h2>{farm.name}</h2>
      {choices.length ? (
        <>
          <p>Choose {action === 'chat' ? 'a chilli crop' : 'your crop'}.</p>
          <ul className="record-rows">
            {choices.map((crop) => (
              <li key={crop.id}>
                <Link to={destination(crop)}>
                  {cropName(crop.crop_type_id, types.data!.items)} · planted{' '}
                  {crop.planting_date}
                </Link>
              </li>
            ))}
          </ul>
        </>
      ) : (
        <p>
          {action === 'chat'
            ? 'No active chilli crops on this page.'
            : 'No active crops on this page.'}
        </p>
      )}
      {records.data.total > records.data.page_size && (
        <Pagination result={records.data} page={page} change={setPage} />
      )}
      <Link to={path + '/new'}>Add a crop</Link>
    </section>
  )
}
